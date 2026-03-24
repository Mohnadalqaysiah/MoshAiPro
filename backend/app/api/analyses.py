"""
Qaffel AI - Analyses History API
سجل التحليلات مع إعادة التحليل
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.analysis_log import AnalysisLog
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/history")
def get_analyses_history(
    limit: int = 50,
    offset: int = 0,
    market: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """سجل كل التحليلات الخاصة بالمستخدم"""
    q = db.query(AnalysisLog).filter(AnalysisLog.user_id == user.id)
    if market:
        q = q.filter(AnalysisLog.market == market.upper())
    total = q.count()
    logs  = q.order_by(AnalysisLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [
            {
                "id":             l.id,
                "market":         l.market,
                "timeframe":      l.timeframe,
                "recommendation": l.recommendation,
                "confidence":     l.confidence,
                "current_price":  l.current_price,
                "entry":          l.entry,
                "sl":             l.sl,
                "tp1":            l.tp1,
                "tp2":            l.tp2,
                "rr":             l.rr,
                "lot_size":       l.lot_size,
                "from_cache":     l.from_cache,
                "created_at":     l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
    }


@router.get("/{log_id}")
def get_analysis_detail(
    log_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """تفاصيل تحليل واحد كامل"""
    log = db.query(AnalysisLog).filter(
        AnalysisLog.id == log_id,
        AnalysisLog.user_id == user.id,
    ).first()
    if not log:
        raise HTTPException(404, "التحليل غير موجود")
    return {
        "id":           log.id,
        "market":       log.market,
        "timeframe":    log.timeframe,
        "created_at":   log.created_at.isoformat() if log.created_at else None,
        "full_result":  log.full_result,
    }
