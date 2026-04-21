"""
Mosh AI Pro v5 - Price Alerts API
تنبيهات السعر: إنشاء، عرض، حذف — والإرسال التلقائي عبر تلغرام
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.database import get_db
from app.models.price_alert import PriceAlert, AlertDirection
from app.services.auth_service import get_current_user

router = APIRouter()

# ── الرموز المدعومة ────────────────────────────────────────────────────────────
SUPPORTED_SYMBOLS = {
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD",
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "NAS100", "US30", "SP500", "USOIL", "BRENT",
}

# ── Schemas ────────────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    symbol:       str
    target_price: float
    direction:    AlertDirection
    note:         Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("")
def create_alert(
    body: AlertCreate,
    db:   Session = Depends(get_db),
    user = Depends(get_current_user),
):
    symbol = body.symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"رمز غير مدعوم: {symbol}")
    if body.target_price <= 0:
        raise HTTPException(400, "السعر المستهدف يجب أن يكون موجباً")

    # حد أقصى 10 تنبيهات نشطة لكل مستخدم
    active = db.query(PriceAlert).filter(
        PriceAlert.user_id  == user.id,
        PriceAlert.triggered == False,
    ).count()
    if active >= 10:
        raise HTTPException(400, "وصلت للحد الأقصى (10 تنبيهات نشطة)")

    alert = PriceAlert(
        user_id      = user.id,
        telegram_id  = user.telegram_id,
        symbol       = symbol,
        target_price = body.target_price,
        direction    = body.direction,
        note         = body.note,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "message": "تم إنشاء التنبيه بنجاح ✅"}


@router.get("")
def list_alerts(
    db:   Session = Depends(get_db),
    user = Depends(get_current_user),
):
    alerts = (
        db.query(PriceAlert)
        .filter(PriceAlert.user_id == user.id)
        .order_by(PriceAlert.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "alerts": [
            {
                "id":           a.id,
                "symbol":       a.symbol,
                "target_price": a.target_price,
                "direction":    a.direction.value,
                "note":         a.note,
                "triggered":    a.triggered,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                "created_at":   a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]
    }


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db:       Session = Depends(get_db),
    user      = Depends(get_current_user),
):
    alert = db.query(PriceAlert).filter(
        PriceAlert.id      == alert_id,
        PriceAlert.user_id == user.id,
    ).first()
    if not alert:
        raise HTTPException(404, "التنبيه غير موجود")
    db.delete(alert)
    db.commit()
    return {"message": "تم حذف التنبيه"}
