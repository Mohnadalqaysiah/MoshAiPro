"""
سجل الأداء العام (2026-10-24، قرار المالك) — /results بالموقع.

**مغلق افتراضياً**: يُفتح بإعداد `public_track_record_enabled = true` من اللوحة، بعد شرط "أسبوعين ممتازين متتاليين"
(DECISIONS 24/10؛ القراءة ~02/11). الأدمن يعاينه قبل الفتح عبر /admin/track-record/*.

مبادئ لا تُكسر (لا عرض انتقائي — حُذف قبلها PublicPerformance.jsx لأنه أخفى الخسائر وثبّت الدقة عند 85%):
  - **كل** القرارات المغلقة منذ بداية حلقة الرصد الموثوقة (OUTCOME_FIX_DATE)، الرابحة والخاسرة والتأمين، قراراً واحداً لكل صفقة.
  - الطريقة مكتوبة على الصفحة: الصفقة رابحة عند وصول الهدف الأول (معيار المالك 16/10)، والنتيجة بمضاعف R.
  - كل صفقة قابلة للتحقق بشموع حقيقية (services/trade_chart.py — نفس مرجع حساب النتيجة).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site_settings import SiteSettings
from app.models.user import User
from app.services.auth_service import get_admin_user

router = APIRouter()
FLAG = "public_track_record_enabled"
RESULTS = {"win": ("TP1_HIT", "TP2_HIT"), "loss": ("SL_HIT",), "breakeven": ("BREAKEVEN",)}


def is_enabled(db: Session) -> bool:
    row = db.query(SiteSettings).filter(SiteSettings.key == FLAG).first()
    return bool(row and (row.value or "").strip().lower() == "true")


def _since(weeks: int):
    from app.services.quality_report import OUTCOME_FIX_DATE
    start = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    start = start - timedelta(days=start.weekday())
    return max(start.replace(hour=0, minute=0, second=0, microsecond=0), OUTCOME_FIX_DATE)


def build_summary(db: Session, weeks: int) -> dict:
    from app.services.quality_report import OUTCOME_FIX_DATE
    from app.services.weekly_markets import closed_decisions, weekly_table
    decs = closed_decisions(db, _since(weeks))
    decided = [d for d in decs if d["status"] != "BREAKEVEN"]
    wins = sum(1 for d in decided if d["status"] != "SL_HIT")
    total_r = sum(d["r"] for d in decided)
    return {
        "since": _since(weeks).date().isoformat(), "baseline": OUTCOME_FIX_DATE.date().isoformat(),
        "decisions": len(decs), "wins": wins, "losses": len(decided) - wins,
        "breakeven": len(decs) - len(decided),
        "win_rate": round(100 * wins / len(decided), 1) if decided else None,
        # (2026-10-30) المتوسط على كل الصفقات المعروض عددها (التأمين 0R صفقة حقيقية) ليُشتق من أرقام الصفحة نفسها
        "total_r": round(total_r, 2), "avg_r": round(total_r / len(decs), 3) if decs else None,
        "weekly": weekly_table(db, weeks),
    }


def build_trades(db: Session, weeks: int, group: Optional[str], result: Optional[str], page: int, page_size: int) -> dict:
    from app.models.signal import Signal
    from app.services.weekly_markets import closed_decisions
    decs = closed_decisions(db, _since(weeks))
    if group:
        decs = [d for d in decs if d["group"] == group]
    if result in RESULTS:
        decs = [d for d in decs if d["status"] in RESULTS[result]]
    decs.sort(key=lambda d: d["created_at"], reverse=True)
    page, page_size = max(1, page), max(1, min(page_size, 50))
    chunk = decs[(page - 1) * page_size: page * page_size]
    tp1 = {s.id: s.take_profit_1 for s in db.query(Signal).filter(Signal.id.in_([d["id"] for d in chunk] or [0])).all()}
    items = [{"id": d["id"], "market": d["market"], "group": d["group"], "timeframe": d["timeframe"], "type": d["side"],
              "status": d["status"], "r": round(d["r"], 2), "entry": d["entry"], "sl": d["stop_loss"],
              "tp1": tp1.get(d["id"]), "tp2": d["tp2"], "created_at": d["created_at"].isoformat()} for d in chunk]
    return {"items": items, "count": len(decs), "page": page, "pages": max(1, -(-len(decs) // page_size))}


async def build_chart_public(db: Session, signal_id: int, weeks: int = 26) -> dict:
    """الشارت فقط لصفقة ضمن السجل نفسه (مغلقة، منذ بداية الحلقة الموثوقة) — لا يكشف مفتوحة ولا ما قبل الخط الأساسي."""
    from app.models.signal import Signal
    from app.services.quality_report import OUTCOME_FIX_DATE
    from app.services.trade_chart import build_chart
    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    created = sig.created_at if sig and sig.created_at and sig.created_at.tzinfo else \
        (sig.created_at.replace(tzinfo=timezone.utc) if sig and sig.created_at else None)
    if not sig or created is None or created < OUTCOME_FIX_DATE:
        raise HTTPException(404, "الصفقة غير موجودة بالسجل")
    res = await build_chart(sig)
    if not res.get("ok"):
        raise HTTPException(400 if "بعد إغلاق" in res["error"] else 503, res["error"])
    return res


# ─── العام (مغلق حتى الفتح) ─────────────────────────────────────────────────
def _require_open(db: Session):
    if not is_enabled(db):
        raise HTTPException(404, "سجل الأداء العام غير متاح بعد")


@router.get("/public/track-record")
def public_summary(weeks: int = 8, db: Session = Depends(get_db)):
    _require_open(db)
    return build_summary(db, max(1, min(weeks, 26)))


@router.get("/public/track-record/trades")
def public_trades(weeks: int = 8, group: Optional[str] = None, result: Optional[str] = None, page: int = 1,
                  page_size: int = 20, db: Session = Depends(get_db)):
    _require_open(db)
    return build_trades(db, max(1, min(weeks, 26)), group, result, page, page_size)


@router.get("/public/track-record/{signal_id}/chart")
async def public_chart(signal_id: int, db: Session = Depends(get_db)):
    _require_open(db)
    return await build_chart_public(db, signal_id)


# ─── معاينة الأدمن (تعمل والسجل مغلق) ───────────────────────────────────────
@router.get("/admin/track-record")
def admin_summary(weeks: int = 8, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return {**build_summary(db, max(1, min(weeks, 26))), "enabled": is_enabled(db)}


@router.get("/admin/track-record/trades")
def admin_trades(weeks: int = 8, group: Optional[str] = None, result: Optional[str] = None, page: int = 1,
                 page_size: int = 20, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return build_trades(db, max(1, min(weeks, 26)), group, result, page, page_size)


@router.get("/admin/track-record/{signal_id}/chart")
async def admin_chart(signal_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return await build_chart_public(db, signal_id)
