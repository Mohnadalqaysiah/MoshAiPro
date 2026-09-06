"""
Mosh AI Pro v5 - Strategy Builder Background Checker
Real "Monitoring" engine: evaluates every ACTIVE strategy against the live
AI engine on an interval and sends a real Telegram alert on trigger.
Same asyncio.create_task + while-True pattern as _price_alert_checker()
in app/main.py.
"""
import asyncio
from datetime import datetime, timezone
from loguru import logger

CHECK_INTERVAL_SEC = 300      # 5 minutes
ALERT_COOLDOWN_SEC = 1800     # 30 minutes — avoid re-alerting every cycle

# per (strategy_id, symbol) last-sent timestamp — resets on restart, same
# spirit as telegram-bot/bot.py's in-memory `last_alert` dict.
_last_sent: dict = {}


def _norm_symbol(sym: str) -> str:
    return sym.replace("/", "").upper()


_LOCK_KEY = 90210001  # arbitrary unique advisory-lock key for this task

async def strategy_checker():
    from app.database import SessionLocal
    from app.models.strategy import Strategy, StrategyStatus, StrategyTriggerEvent
    from app.models.user import UserRole, PlanType
    from app.services.strategy_engine import (
        evaluate_strategy, build_telegram_message, distinct_timeframes, primary_timeframe,
    )
    from app.services.ai_engine_v5 import mosh_ai_engine_v5
    from app.services.admin_notify import get_bot_token
    from app.services.worker_lock import try_acquire_singleton_lock
    import aiohttp

    # production runs multiple uvicorn workers — only one of them should
    # actually run this loop, or triggered strategies would alert Telegram
    # once per worker.
    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Strategy checker")
    if lock_conn is None:
        return

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                active = db.query(Strategy).filter(Strategy.status == StrategyStatus.ACTIVE).all()
                if not active:
                    continue

                for s in active:
                    # Strategy Builder alerting is subscriber-exclusive — if the
                    # owner's subscription lapsed since activation, stop here
                    # rather than keep alerting a now-trial/expired account.
                    owner = s.user
                    if not owner or (owner.role != UserRole.ADMIN and owner.plan not in (PlanType.WEEKLY, PlanType.MONTHLY)):
                        continue

                    conditions = [c for g in s.groups for c in g.conditions]
                    if not conditions or not s.symbols:
                        continue
                    # (2026-09-06) كل شرط له فريمه الخاص — تحليل حقيقي مستقل لكل
                    # فريم فريد مستخدم فعليًا، مش فريم واحد مُختار اعتباطيًا
                    # (البَق الأصلي: فرز أبجدي بيختار "1H" قبل "1D" رغم إنه أصغر).
                    tfs = distinct_timeframes(conditions)
                    primary_tf = primary_timeframe(conditions)

                    for symbol in s.symbols:
                        try:
                            analyses = await mosh_ai_engine_v5.analyze_market_multi_tf(_norm_symbol(symbol), tfs)
                        except Exception as e:
                            logger.warning(f"Strategy checker: analyze failed {symbol}/{tfs}: {e}")
                            continue
                        primary_analysis = analyses.get(primary_tf) or next(iter(analyses.values()), {})

                        result = evaluate_strategy(
                            s.groups, conditions, analyses, s.min_score,
                            price=primary_analysis.get("current_price"),
                        )

                        telegram_sent = False
                        if result["triggered"] and s.trigger_send_telegram and s.tg_enabled:
                            key = (s.id, symbol)
                            last = _last_sent.get(key)
                            now = datetime.now(timezone.utc)
                            cooled_down = not last or (now - last).total_seconds() >= ALERT_COOLDOWN_SEC
                            chat_id = s.tg_chat_override or (s.user.telegram_id if s.user else None)
                            token = get_bot_token()
                            if cooled_down and chat_id and token:
                                text = build_telegram_message(s, result, symbol, primary_tf, primary_analysis)
                                url = f"https://api.telegram.org/bot{token}/sendMessage"
                                try:
                                    async with aiohttp.ClientSession() as sess:
                                        await sess.post(url, json={"chat_id": chat_id, "text": text},
                                                         timeout=aiohttp.ClientTimeout(total=10))
                                    telegram_sent = True
                                    _last_sent[key] = now
                                    logger.info(f"🎯 Strategy triggered & alerted: {s.name} / {symbol}")
                                except Exception as e:
                                    logger.warning(f"Strategy checker: telegram send failed: {e}")

                        if result["triggered"]:
                            s.last_triggered_at = datetime.now(timezone.utc)

                        db.add(StrategyTriggerEvent(
                            # عمود timeframe فردي بقاعدة البيانات — نسجّل كل الأطر
                            # الفريدة المستخدمة فعلياً بهالتقييم (مفصولة بفاصلة)
                            # بدل فريم واحد مضلّل لاستراتيجية متعددة الأطر.
                            strategy_id=s.id, symbol=symbol, timeframe=",".join(tfs),
                            score=result["score"], triggered=result["triggered"],
                            matched_json=result["matched"], price=result["price"],
                            telegram_sent=telegram_sent,
                        ))
                db.commit()
            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Strategy checker error: {e}")

    lock_conn.close()
