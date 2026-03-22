"""
Mosh AI Pro v5 - Signals API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.services.ai_engine_v5 import mosh_ai_engine_v5
from app.models import Signal
from app.models.user import User, PlanType
from app.services.auth_service import get_current_user, check_subscription, deduct_trial

router = APIRouter()


@router.post("/analyze")
async def analyze_market(
    symbol: str,
    timeframe: str = "1h",
    advanced_mode: bool = True,
    force_refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """تحليل السوق مع فحص الصلاحية وكاش ذكي"""
    status = check_subscription(user, db)
    if not status["allowed"]:
        raise HTTPException(status_code=403, detail=status["reason"])

    if user.plan == PlanType.TRIAL and user.trial_analyses_left <= 0:
        raise HTTPException(
            status_code=403,
            detail="استهلكت تحليلات التجربة المجانية. اشترك للمتابعة."
        )

    try:
        # من الكاش؟ لا نخصم كريدت
        analysis = await mosh_ai_engine_v5.analyze_market(
            symbol=symbol,
            timeframe=timeframe,
            advanced_mode=advanced_mode,
            force_refresh=force_refresh,
            account_balance=float(getattr(user, "account_balance", 10000.0) or 10000.0),
            max_risk_percent=float(getattr(user, "risk_percent", 1.5) or 1.5),
        )

        # نخصم كريدت فقط إذا كان تحليلاً جديداً (مش من الكاش)
        if not analysis.get("from_cache", False):
            if user.plan == PlanType.TRIAL:
                deduct_trial(user, db, kind="analysis")
            else:
                user.analyses_total     += 1
                user.analyses_used_today += 1
                db.commit()


        return {"success": True, "data": analysis}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_signals(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get latest signals
    """
    try:
        signals = db.query(Signal).order_by(
            Signal.created_at.desc()
        ).limit(limit).all()
        
        return {
            "success": True,
            "count": len(signals),
            "data": [
                {
                    "id": s.id,
                    "market": s.market,
                    "signal_type": s.signal_type.value,
                    "entry_price": s.entry_price,
                    "status": s.status.value,
                    "ai_confidence": s.ai_confidence,
                    "created_at": s.created_at.isoformat()
                }
                for s in signals
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{signal_id}")
async def get_signal_details(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed signal information
    """
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        return {
            "success": True,
            "data": {
                "id": signal.id,
                "market": signal.market,
                "timeframe": signal.timeframe,
                "signal_type": signal.signal_type.value,
                "signal_quality": signal.signal_quality.value,
                "status": signal.status.value,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit_1": signal.take_profit_1,
                "take_profit_2": signal.take_profit_2,
                "current_price": signal.current_price,
                "ai_confidence": signal.ai_confidence,
                "ai_reasoning": signal.ai_reasoning,
                "wyckoff_phase": signal.wyckoff_phase,
                "premium_discount": signal.premium_discount,
                "killzone": signal.killzone,
                "risk_reward_ratio": signal.risk_reward_ratio,
                "profit_loss": signal.profit_loss,
                "profit_loss_percentage": signal.profit_loss_percentage,
                "created_at": signal.created_at.isoformat(),
                "expires_at": signal.expires_at.isoformat() if signal.expires_at else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching signal details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
