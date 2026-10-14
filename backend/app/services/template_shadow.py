"""
Template Shadow (2026-10-15) — تجربة صامتة لقوالب الاستراتيجيات على توصيات الذهب.

سؤال المالك: لماذا لا نعتمد "قنّاص الجلسات — بيع" لتوصيات المنصة؟ الجواب (DECISIONS.md 15/10): نتيجته من
شهر هابط واحد، واختير الأفضل من 8 — يلزم إثباته على أيام **لم يُختبر عليها**. هذه المهمة تفعل ذلك:

  - كل 6 ساعات تشغّل نفس الباكتيست (run_backtest_sync — نفس المحرك ونفس محاسبة النصف عند TP1 والتعادل
    وخصم السبريد) على آخر 3 أيام لكل قالب في SHADOW_TEMPLATES.
  - تُحفظ فقط الصفقات المُطلقة بعد SHADOW_START (القالب ثُبّت قبلها — فهي خارج العينة فعلاً)، والمغلقة.
  - صفقة واحدة مفتوحة لكل قالب عبر التشغيلات: صفقة تبدأ قبل خروج آخر صفقة محفوظة تُتجاهل.
  - تُحفظ بجدول shadow_signals (reason = "tpl:<key>") والنتيجة نهائية (shadow_evaluator لا يلمسها).

لا ترسل شيئاً لأي مستخدم ولا تلمس جدول signals. التقرير: diag_template_shadow.py.
"""
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
from loguru import logger

SHADOW_START = datetime(2026, 10, 16, tzinfo=timezone.utc)
SHADOW_TEMPLATES = ["gold_session_sell", "gold_session_buy", "gold_session_trend_buy", "gold_session_trend_sell"]
RUN_INTERVAL_SEC = 6 * 3600
LOOKBACK_DAYS = 3            # > أقصى مدة صفقة (24 ساعة) + فجوة العطلة
_LOCK_KEY = 90210007         # 90210001..90210006 مستخدَمة
_OUTCOME = {"TP2": "TP2_HIT", "TP1+BE": "TP1_BE", "SL": "SL_HIT", "EXPIRED": "EXPIRED"}


def template_snapshot(t: dict) -> dict:
    """نفس شكل strategy_backtest.snapshot لكن من قالب (لا صف استراتيجية بالقاعدة)."""
    groups, conds = [], []
    for gi, g in enumerate(t["groups"]):
        groups.append(SimpleNamespace(id=gi + 1, name=g["name"], logic=SimpleNamespace(value=g["logic"]),
                                      at_least=g.get("atLeast") or 1))
        for c in g["conditions"]:
            conds.append(SimpleNamespace(id=len(conds) + 1, group_id=gi + 1, type=c["type"], label=c["label"],
                                         timeframe=c["timeframe"], value=c["value"], weight=c["weight"],
                                         enabled=True, negate=False))
    return {"groups": groups, "conditions": conds, "min_score": t["min_score"],
            "rr": float(t["exec"]["rr"]), "symbols": t["symbols"], "name": t["name"]}


def _ts(v):
    d = pd.Timestamp(v).to_pydatetime()
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def save_trades(db, key: str, symbol: str, trades: list) -> int:
    from app.models.shadow_signal import ShadowSignal
    reason = f"tpl:{key}"
    last = (db.query(ShadowSignal.exit_time).filter(ShadowSignal.reason == reason)
              .order_by(ShadowSignal.exit_time.desc()).first())
    busy_until = last[0] if last else None
    if busy_until is not None and busy_until.tzinfo is None:
        busy_until = busy_until.replace(tzinfo=timezone.utc)
    n = 0
    for tr in sorted(trades, key=lambda x: x["time"]):
        t0, t1 = _ts(tr["time"]), _ts(tr["exit_time"])
        if t0 < SHADOW_START or (busy_until is not None and t0 < busy_until):
            continue
        h = hashlib.md5(f"{reason}-{tr['time']}".encode()).hexdigest()
        if db.query(ShadowSignal.id).filter(ShadowSignal.signal_hash == h).first():
            continue
        db.add(ShadowSignal(
            source="template", reason=reason, market=symbol.replace("/", "").upper(), timeframe="15m",
            signal_type=tr["side"], entry_price=tr["entry"], stop_loss=tr["sl"], take_profit_1=tr["tp1"],
            take_profit_2=tr["tp2"], signal_hash=h, created_at=t0, expires_at=t0 + timedelta(hours=24),
            outcome=("EXPIRED_TP1" if tr["result"] == "EXPIRED" and tr.get("tp1_hit") else _OUTCOME.get(tr["result"], tr["result"])), r_multiple=tr["r"], entry_time=t0, exit_time=t1,
            evaluated_at=datetime.now(timezone.utc),
        ))
        busy_until = t1
        n += 1
    db.commit()
    return n


async def run_once() -> int:
    from app.database import SessionLocal
    from app.services.strategy_templates import get_template
    from app.services.strategy_backtest import run_backtest_sync, _LOCK

    total = 0
    loop = asyncio.get_running_loop()
    for key in SHADOW_TEMPLATES:
        t = get_template(key)
        if not t:
            continue
        async with _LOCK:      # نفس قفل باكتيست المستخدمين — لا تشغيلان على المعالج معاً
            res = await loop.run_in_executor(None, run_backtest_sync, template_snapshot(t), t["symbols"], LOOKBACK_DAYS)
        db = SessionLocal()
        try:
            for sym in t["symbols"]:
                total += save_trades(db, key, sym, [x for x in res["trades"] if x.get("symbol") == sym])
        finally:
            db.close()
    return total


async def template_shadow():
    from app.services.worker_lock import try_acquire_singleton_lock

    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Template shadow")
    if lock_conn is None:
        return
    logger.success("✅ Template shadow started")
    while True:
        try:
            await asyncio.sleep(RUN_INTERVAL_SEC)
            if datetime.now(timezone.utc) < SHADOW_START:
                continue
            n = await run_once()
            if n:
                logger.info(f"🌑 Template shadow: {n} صفقة قالب جديدة")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Template shadow error: {e}")
    lock_conn.close()
