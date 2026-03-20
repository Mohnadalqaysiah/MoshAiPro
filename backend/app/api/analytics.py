"""
Mosh AI Pro v5 - Analytics API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.database import get_db
from app.models import Signal, SignalStatus

router = APIRouter()


@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get overall performance metrics
    """
    try:
        # Total signals
        total_signals = db.query(func.count(Signal.id)).scalar()
        
        # Win rate
        successful = db.query(func.count(Signal.id)).filter(
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT])
        ).scalar()
        
        failed = db.query(func.count(Signal.id)).filter(
            Signal.status == SignalStatus.SL_HIT
        ).scalar()
        
        win_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
        
        # Average profit/loss
        avg_profit = db.query(func.avg(Signal.profit_loss_percentage)).filter(
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT])
        ).scalar() or 0
        
        # Total profit/loss
        total_profit = db.query(func.sum(Signal.profit_loss)).filter(
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT])
        ).scalar() or 0
        
        return {
            "success": True,
            "data": {
                "total_signals": total_signals,
                "successful_signals": successful,
                "failed_signals": failed,
                "win_rate": round(win_rate, 2),
                "average_profit_percentage": round(float(avg_profit), 2),
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
    """
    try:
        total = db.query(func.count(Signal.id)).filter(Signal.market == market).scalar()
        
        successful = db.query(func.count(Signal.id)).filter(
            Signal.market == market,
            Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT])
        ).scalar()
        
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
