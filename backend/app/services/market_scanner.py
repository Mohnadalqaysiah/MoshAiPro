"""
Mosh AI Pro v5 - Market Scanner Background Checker
Automatically feeds broadcast_new_signals (telegram-bot/bot.py) instead of
depending only on users manually triggering /analyze or a symbol being on
someone's personal watchlist — that gap is why "active" markets with no
watcher never actually produced a signal (see SIGNALS_STRATEGY.md §7 and
the 2026-08-30 monitor_watchlists scope investigation).

Reuses bot_analyze()'s exact save path (analyze_market → _has_active_signal
→ _check_loss_streak_breaker → save), no parallel logic — this module just
calls it in a loop, attributed to a dedicated system account with no
Telegram/watchlist of its own so broadcast_new_signals fans it out to every
real subscriber (its own watchlist filter already handles "user with no
watchlist gets everything, user with a watchlist gets only their symbols").

Pilot scope (2026-08-30): 20 non-Gulf symbols, 30-minute cycle, 3
timeframes — deliberately not all ~53 active markets. Widen only after
24-48h of monitoring load / signal volume / rate-limit headroom. Same
asyncio.create_task + while-True + singleton-lock pattern as
strategy_checker.py / _price_alert_checker() in app/main.py.
"""
import asyncio
from loguru import logger

CHECK_INTERVAL_SEC = 1800   # 30 minutes — pilot phase, was 15 min in the original proposal
CALL_SPACING_SEC   = 3      # gap between individual analyze_market() calls

# Pilot list (2026-08-30): the 16 non-Gulf symbols added today +
# XAUUSD/XAGUSD/BTCUSD/ETHUSD (highest signal volume today). NOT the full
# active-markets list on purpose — see module docstring.
SCAN_SYMBOLS = [
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD",
    "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "DXY",
    "COPPER", "XPTUSD",
    "BNBUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD",
    "AMD", "NFLX",
]
SCAN_TIMEFRAMES = ["15m", "1h", "4h"]   # 20 × 3 = 60 analyze_market() calls/cycle

SYSTEM_SCANNER_EMAIL = "system-scanner@qaffel.internal"

_LOCK_KEY = 90210003  # arbitrary unique advisory-lock key — 90210001/2 already used


async def market_scanner():
    from app.database import SessionLocal
    from app.models.user import User
    from app.api.bot import bot_analyze
    from app.services.smart_data import smart_data as _sd
    from app.services.worker_lock import try_acquire_singleton_lock

    # production runs multiple uvicorn workers — only one of them should
    # actually run this loop, or every symbol would be analyzed (and
    # potentially saved/broadcast) once per worker.
    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Market scanner")
    if lock_conn is None:
        return

    db0 = SessionLocal()
    try:
        system_user = db0.query(User).filter(User.email == SYSTEM_SCANNER_EMAIL).first()
    finally:
        db0.close()

    if not system_user:
        logger.error(
            f"Market scanner: system account ({SYSTEM_SCANNER_EMAIL}) not found — "
            f"run migrate_add_system_scanner_user.py first. Task will not run this session."
        )
        lock_conn.close()
        return
    system_user_id = system_user.id
    logger.success(f"✅ Market scanner started — {len(SCAN_SYMBOLS)} symbols × {len(SCAN_TIMEFRAMES)} timeframes, every {CHECK_INTERVAL_SEC//60}min")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            attempted = 0
            actionable = 0   # recommendation was BUY/SELL (not necessarily saved — gates may still reject)
            errors = 0

            for symbol in SCAN_SYMBOLS:
                if not _sd.is_market_open(symbol):
                    continue
                for tf in SCAN_TIMEFRAMES:
                    db = SessionLocal()
                    try:
                        result = await bot_analyze(
                            symbol=symbol, timeframe=tf, telegram_id="",
                            system_user_id=system_user_id, _=True, db=db,
                        )
                        attempted += 1
                        rec = (result.get("data") or {}).get("recommendation")
                        if rec in ("BUY", "SELL"):
                            actionable += 1
                    except Exception as e:
                        errors += 1
                        logger.warning(f"Market scanner: {symbol}/{tf} failed: {e}")
                    finally:
                        db.close()
                    await asyncio.sleep(CALL_SPACING_SEC)

            logger.info(
                f"🛰️ Market scanner cycle done — attempted={attempted} "
                f"actionable={actionable} errors={errors}"
            )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Market scanner error: {e}")

    lock_conn.close()
