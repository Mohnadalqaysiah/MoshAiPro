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
