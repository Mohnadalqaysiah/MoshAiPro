"""
Learning Games API (2026-10-11)
================================
/api/v1/games/progress    GET/PUT  (مسجّل)  — حفظ تقدّم اللعبة بالحساب
/api/v1/games/leaderboard GET      (عام)    — متصدرو الأسبوع

النقاط تُحسب في المتصفح، فلا يمكن جعلها مضمونة ضد التلاعب. الحماية هنا
معقولة لا مطلقة: الخادم يقبل زيادة النقاط بمعدّل يستطيعه لاعب حقيقي فقط
(أقصى جواب = 50 نقطة: (15 + 10 سلسلة) × 2 للخبير)، وما فوقه يُقصّ. لذلك أي
جائزة مرتبطة باللوحة تبقى متواضعة وتُراجَع يدوياً قبل منحها.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Body
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.game_progress import GameProgress, GameEventDaily
from app.services.auth_service import get_current_user, get_admin_user, bearer, decode_token

router = APIRouter()

MAX_POINTS_PER_MIN = 500     # ~10 إجابات مثالية بالدقيقة بأعلى مستوى
MAX_POINTS_PER_SAVE = 3000


def _week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def _display_name(u: User) -> str:
    """اسم مختصر للوحة — الاسم الأول أو بداية البريد، بلا كشف البريد كاملاً."""
    if u.full_name and u.full_name.strip():
        return u.full_name.strip().split()[0][:16]
    local = (u.email or "لاعب").split("@")[0]
    return (local[:3] + "***") if len(local) > 3 else "لاعب"


@router.get("/progress")
def get_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gp = db.query(GameProgress).filter(GameProgress.user_id == user.id).first()
    return {"data": gp.data if gp else None, "points": gp.points if gp else 0}


@router.put("/progress")
def save_progress(
    data: dict = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    wk = _week_key(now)
    gp = db.query(GameProgress).filter(GameProgress.user_id == user.id).first()
    if gp is None:
        gp = GameProgress(user_id=user.id, points=0, best_streak=0, week_key=wk, week_points=0)
        db.add(gp)
        last = None
    else:
        last = gp.updated_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

    try:
        claimed = max(0, int(data.get("points") or 0))
        streak = max(0, int(data.get("bestStreak") or 0))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "invalid"}

    # معدّل الزيادة: أول حفظ يقبل حتى سقف الحفظ الواحد (نقاط لعبها قبل التسجيل)
    minutes = max(1.0, (now - last).total_seconds() / 60) if last else 1.0
    allowed = min(MAX_POINTS_PER_SAVE, int(MAX_POINTS_PER_MIN * minutes))
    delta = max(0, claimed - (gp.points or 0))
    accepted = min(delta, allowed)

    if gp.week_key != wk:
        gp.week_key, gp.week_points = wk, 0
    gp.points = (gp.points or 0) + accepted
    gp.week_points = (gp.week_points or 0) + accepted
    gp.best_streak = max(gp.best_streak or 0, min(streak, 500))
    blob = dict(data)
    blob["points"] = gp.points          # الصفحة تتبنى رقم الخادم إن قُصّ
    gp.data = blob
    gp.updated_at = now
    db.commit()
    return {"ok": True, "points": gp.points, "week_points": gp.week_points, "capped": accepted < delta}


# ─── صفقات كفيل الحقيقية (2026-10-11) ─────────────────────────────────────────
# إشارات حقيقية أُرسلت للمشتركين ونتيجتها المسجّلة، مع شموعها قبل وبعد الإشارة.
# **عيّنة عشوائية لا منتقاة** — تشمل الخسائر بنتيجتها الحقيقية (قاعدة: لا إخفاء
# للخسائر ولا ادعاء أداء لا يُثبت). النتائج منذ 24/09 (بعد تصحيح حلقة الرصد).
# الشموع بنفس مرجع بناء المستويات: الذهب والفضة TV الفوري، وغيرهما yfinance.
# المؤشرات وأسهم الخليج مستبعدة (مرجع سعر مختلف أو بيانات متقطعة).
import asyncio as _asyncio
import random as _random
import time as _time

_REAL_MARKETS = {"XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"}
_REAL_TF_MIN = {"15m": 15, "1h": 60, "4h": 240}
_REAL_POOL: dict = {"at": 0.0, "items": []}
_REAL_LOCK = _asyncio.Lock()
_REAL_TTL = 6 * 3600
_REAL_SINCE = datetime(2026, 9, 24, tzinfo=timezone.utc)


def _real_candles_sync(market: str, tf: str):
    """[(epoch, o, h, l, c), ...] لغير المعادن من yfinance (مرجع مستوياتها)."""
    import yfinance as yf
    import pandas as pd
    from app.services.smart_data import _resolve_yf_symbol
    interval = "15m" if tf == "15m" else "1h"
    h = yf.Ticker(_resolve_yf_symbol(market)).history(period="60d", interval=interval, auto_adjust=True)
    if h is None or not len(h):
        return []
    h.index = pd.to_datetime(h.index, utc=True)
    if tf == "4h":
        h = h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return [(t.timestamp(), float(r.Open), float(r.High), float(r.Low), float(r.Close)) for t, r in h.iterrows()]


async def _real_candles(market: str, tf: str):
    if market in ("XAUUSD", "XAGUSD"):
        from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
        bars = await fetch_tv_history(TV_SYMBOL_MAP[market], tf, bars=3000, timeout_s=40)
        return [(float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4])) for b in (bars or [])]
    return await _asyncio.get_event_loop().run_in_executor(None, _real_candles_sync, market, tf)


async def _build_real_pool(db: Session) -> list:
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import group_unique_decisions
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= _REAL_SINCE,
        Signal.market.in_(list(_REAL_MARKETS)),
        Signal.timeframe.in_(list(_REAL_TF_MIN)),
        Signal.broadcast_sent == True,  # noqa: E712 — وصلت المشتركين فعلاً
    ).all()
    by_id = {s.id: s for s in rows}
    groups = group_unique_decisions(rows)
    picks = _random.sample(groups, min(16, len(groups)))      # عشوائي — لا انتقاء

    cache: dict = {}
    items = []
    for g in picks:
        s = by_id[g["id"]]
        key = (s.market, s.timeframe)
        if key not in cache:
            try:
                cache[key] = await _real_candles(*key)
            except Exception:
                cache[key] = []
        cs = cache[key]
        if not cs:
            continue
        created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
        exited = s.exit_executed
        if exited is not None and exited.tzinfo is None:
            exited = exited.replace(tzinfo=timezone.utc)
        c_ts, step = created.timestamp(), _REAL_TF_MIN[s.timeframe] * 60
        before = [c for c in cs if c[0] + step <= c_ts][-40:]
        after_all = [c for c in cs if c[0] + step > c_ts]
        if len(before) < 25 or not after_all:
            continue
        stop_ts = (exited.timestamp() if exited else c_ts) + 3 * step
        after = [c for c in after_all if c[0] <= stop_ts][:45] or after_all[:10]
        status = s.status.value if hasattr(s.status, "value") else s.status
        items.append({
            "market": s.market, "timeframe": s.timeframe,
            "side": s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type,
            "date": created.date().isoformat(),
            "entry": float(s.entry_price), "sl": float(s.stop_loss),
            "tp1": float(s.take_profit_1), "tp2": float(s.take_profit_2 or s.take_profit_1),
            "confidence": round(float(s.ai_confidence or 0)),
            "outcome": status,
            "before": [[round(x, 6) for x in c[1:]] for c in before],
            "after": [[round(x, 6) for x in c[1:]] for c in after],
        })
        await _asyncio.sleep(0.3)
    return items


@router.get("/real-trades")
async def real_trades(limit: int = 6, db: Session = Depends(get_db)):
    """عيّنة عشوائية من صفقات حقيقية بنتائجها — للعبة "صفقات كفيل الحقيقية"."""
    async with _REAL_LOCK:
        if _time.time() - _REAL_POOL["at"] > _REAL_TTL or not _REAL_POOL["items"]:
            try:
                _REAL_POOL["items"] = await _build_real_pool(db)
            except Exception:
                _REAL_POOL["items"] = _REAL_POOL["items"] or []
            _REAL_POOL["at"] = _time.time()
    items = _REAL_POOL["items"]
    pick = _random.sample(items, min(max(1, min(limit, 10)), len(items))) if items else []
    wins = sum(1 for i in items if i["outcome"] in ("TP1_HIT", "TP2_HIT"))
    return {"trades": pick, "pool": len(items), "pool_wins": wins}


_EVENTS = {"visit", "round_done", "signup_click"}


@router.post("/event")
def track_event(
    event: str = Body(..., embed=True),
    embed: bool = Body(False, embed=True),
    db: Session = Depends(get_db),
):
    """عدّاد يومي مجهول الهوية لقياس أثر الألعاب. حدث خارج القائمة يُتجاهل."""
    if event not in _EVENTS:
        return {"ok": False}
    today = datetime.now(timezone.utc).date()
    row = db.query(GameEventDaily).filter(
        GameEventDaily.day == today, GameEventDaily.event == event, GameEventDaily.embed == bool(embed)
    ).first()
    if row is None:
        row = GameEventDaily(day=today, event=event, embed=bool(embed), count=0)
        db.add(row)
    row.count = (row.count or 0) + 1
    try:
        db.commit()
    except Exception:
        db.rollback()        # سباق إنشاء نفس الصف — يضيع عدّ واحد، مقبول
    return {"ok": True}


@router.get("/stats")
def game_stats(
    days: int = 14,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """للأدمن: عدّادات آخر N يوم + عدد اللاعبين المسجّلين."""
    since = datetime.now(timezone.utc).date() - timedelta(days=max(1, min(days, 90)) - 1)
    rows = db.query(GameEventDaily).filter(GameEventDaily.day >= since).order_by(GameEventDaily.day).all()
    by_day: dict = {}
    for r in rows:
        d = by_day.setdefault(r.day.isoformat(), {"visit": 0, "round_done": 0, "signup_click": 0,
                                                   "visit_public": 0, "signup_click_public": 0})
        d[r.event] += r.count
        if not r.embed and r.event in ("visit", "signup_click"):
            d[f"{r.event}_public"] += r.count
    return {
        "days": by_day,
        "registered_players": db.query(GameProgress).count(),
        "week_active_players": db.query(GameProgress).filter(
            GameProgress.week_key == _week_key(datetime.now(timezone.utc)), GameProgress.week_points > 0
        ).count(),
    }


@router.get("/leaderboard")
def leaderboard(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
):
    wk = _week_key(datetime.now(timezone.utc))
    rows = (db.query(GameProgress, User)
            .join(User, User.id == GameProgress.user_id)
            .filter(GameProgress.week_key == wk, GameProgress.week_points > 0)
            .order_by(GameProgress.week_points.desc())
            .limit(10).all())
    top = [{"rank": i + 1, "name": _display_name(u), "points": gp.week_points}
           for i, (gp, u) in enumerate(rows)]

    me = None
    if creds:
        payload = decode_token(creds.credentials)
        if payload:
            gp = db.query(GameProgress).filter(GameProgress.user_id == int(payload["sub"])).first()
            if gp and gp.week_key == wk:
                ahead = db.query(GameProgress).filter(
                    GameProgress.week_key == wk, GameProgress.week_points > gp.week_points
                ).count()
                me = {"rank": ahead + 1, "points": gp.week_points}
    return {"week": wk, "top": top, "me": me}
