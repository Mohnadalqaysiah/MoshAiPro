"""
Reviews API (2026-10-17) — آراء المشتركين الحقيقية فقط (app/models/review.py، DECISIONS.md 17/10).

  POST /api/v1/reviews            (مصادقة) مشترك مدفوع مضى على أول دفعة مقبولة له 7 أيام — رأي واحد، تعديله يعيده "بانتظار المراجعة"
  GET  /api/v1/reviews/mine       (مصادقة) رأيي + هل يحق لي الكتابة ولماذا
  GET  /api/v1/public/reviews     (عام) المعتمدة فقط، الأحدث أولاً، والملخص من المعتمدة فقط. كاش 5 دقائق.
الأدمن (اعتماد/رفض/رد/إدخال رأي حقيقي وصل خارج المنصة) في admin.py.
"""
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.models.review import Review
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()

MIN_DAYS_PAID = 7
MARKET_TAGS = {"gold", "crypto", "forex", "stocks", "learn"}
_CACHE: dict = {}
_CACHE_TTL = 300


def _first_paid(db: Session, user_id: int):
    p = (db.query(Payment).filter(Payment.user_id == user_id, Payment.status == PaymentStatus.APPROVED,
                                  Payment.exclude_from_stats == False)  # noqa: E712
           .order_by(Payment.created_at.asc()).first())
    return p


def _eligibility(db: Session, user: User) -> dict:
    p = _first_paid(db, user.id)
    if not p:
        return {"eligible": False, "reason": "no_paid", "days_left": None}
    since = p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - since).days
    if days < MIN_DAYS_PAID:
        return {"eligible": False, "reason": "too_soon", "days_left": MIN_DAYS_PAID - days, "since": since}
    return {"eligible": True, "reason": None, "days_left": 0, "since": since}


def _public_item(r: Review) -> dict:
    return {
        "id": r.id, "rating": r.rating, "text": r.text, "display_name": r.display_name, "city": r.city,
        "market_tag": r.market_tag, "plan": r.plan_at_review, "source": r.source, "source_note": r.source_note,
        "verified": r.source == "member",
        "subscribed_since": r.subscribed_since.isoformat() if r.subscribed_since else None,
        "admin_reply": r.admin_reply,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


class ReviewIn(BaseModel):
    rating: int
    text: str
    display_name: str
    city: Optional[str] = None
    market_tag: Optional[str] = None
    consent_public: bool = False


@router.post("/reviews")
def submit_review(data: ReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    el = _eligibility(db, user)
    if not el["eligible"]:
        raise HTTPException(403, "كتابة الرأي متاحة للمشتركين بعد 7 أيام من أول اشتراك مدفوع"
                            if el["reason"] == "no_paid" else f"يمكنك كتابة رأيك بعد {el['days_left']} يوم")
    text = (data.text or "").strip()
    name = (data.display_name or "").strip()
    if not 1 <= int(data.rating) <= 5:
        raise HTTPException(400, "التقييم من 1 إلى 5")
    if not 20 <= len(text) <= 600:
        raise HTTPException(400, "النص بين 20 و600 حرف")
    if not 2 <= len(name) <= 40:
        raise HTTPException(400, "الاسم المعروض بين 2 و40 حرفاً")
    if not data.consent_public:
        raise HTTPException(400, "يلزم الموافقة على نشر الرأي")
    tag = data.market_tag if data.market_tag in MARKET_TAGS else None
    p = _first_paid(db, user.id)
    plan = p.plan.value if p and hasattr(p.plan, "value") else (str(p.plan) if p else None)
    last = (db.query(Payment).filter(Payment.user_id == user.id, Payment.status == PaymentStatus.APPROVED)
              .order_by(Payment.created_at.desc()).first())
    if last:
        plan = last.plan.value if hasattr(last.plan, "value") else str(last.plan)

    r = db.query(Review).filter(Review.user_id == user.id).first()
    if not r:
        r = Review(user_id=user.id, source="member")
        db.add(r)
    r.rating, r.text, r.display_name = int(data.rating), text, name
    r.city = (data.city or "").strip()[:40] or None
    r.market_tag, r.plan_at_review, r.subscribed_since = tag, plan, el["since"]
    r.consent_public = True
    r.status, r.approved_at, r.reject_reason = "pending", None, None     # أي تعديل يعود للمراجعة
    db.commit()
    _CACHE.clear()
    return {"success": True, "status": "pending"}


@router.get("/reviews/mine")
def my_review(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    el = _eligibility(db, user)
    r = db.query(Review).filter(Review.user_id == user.id).first()
    return {
        "eligible": el["eligible"], "reason": el["reason"], "days_left": el["days_left"],
        "review": None if not r else {**_public_item(r), "status": r.status, "reject_reason": r.reject_reason},
    }


@router.get("/public/reviews")
def public_reviews(market: Optional[str] = Query(default=None), limit: int = Query(default=12, ge=1, le=50),
                   db: Session = Depends(get_db)):
    key = (market or "all", limit)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]
    approved = db.query(Review).filter(Review.status == "approved", Review.consent_public == True)  # noqa: E712
    all_rows = approved.all()
    dist = {str(k): 0 for k in range(1, 6)}
    for r in all_rows:
        dist[str(r.rating)] += 1
    n = len(all_rows)
    q = approved
    if market in MARKET_TAGS:
        q = q.filter(Review.market_tag == market)
    items = q.order_by(Review.approved_at.desc().nullslast(), Review.created_at.desc()).limit(limit).all()
    out = {
        "summary": {"count": n, "average": round(sum(r.rating for r in all_rows) / n, 2) if n else None,
                    "distribution": dist,
                    "members": sum(1 for r in all_rows if r.source == "member")},
        "items": [_public_item(r) for r in items],
    }
    _CACHE[key] = (time.time(), out)
    return out


def clear_cache():
    _CACHE.clear()
