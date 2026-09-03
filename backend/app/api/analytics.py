"""
Mosh AI Pro v5 - Analytics API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.database import get_db
from app.models import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions

router = APIRouter()


@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get overall performance metrics

    (2026-09-03) نفس إصلاح signals.py/markets.py — كانت تحسب COUNT/SUM
    مباشرة بـSQL على الصفوف الخام (مو مُستخدمة حالياً من الفرونت إند،
    بس نفس نمط الباگ بالضبط لو انفعّلت لاحقاً). صار الجلب أولاً ثم
    التجميع بايثون عبر verified_unique_decisions، راجع
    app/services/decision_grouping.py.
    """
    try:
        closed_raw = db.query(Signal).filter(
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT])
        ).all()
        decisions = verified_unique_decisions(closed_raw)

        total_signals = len(decisions)
        successful = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
        failed     = sum(1 for d in decisions if d["status"] == "SL_HIT")
        win_rate   = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
        total_profit = sum(d["points"] for d in decisions)

        return {
            "success": True,
            "data": {
                "total_signals": total_signals,
                "successful_signals": successful,
                "failed_signals": failed,
                "win_rate": round(win_rate, 2),
                "total_profit_loss": round(float(total_profit), 2)
            }
        }

    except Exception as e:
        logger.error(f"❌ Error fetching performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/{market}/stats")
async def get_market_statistics(market: str, db: Session = Depends(get_db)):
    """
    Get statistics for a specific market

    (2026-09-03) نفس الإصلاح — راجع get_performance_metrics فوق.
    """
    try:
        raw = db.query(Signal).filter(
            Signal.market == market,
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        ).all()
        decisions = verified_unique_decisions(raw)

        total = len(decisions)
        successful = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
        win_rate = (successful / total * 100) if total > 0 else 0

        return {
            "success": True,
            "market": market,
            "data": {
                "total_signals": total,
                "successful": successful,
                "win_rate": round(win_rate, 2)
            }
        }

    except Exception as e:
        logger.error(f"❌ Error fetching market stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
