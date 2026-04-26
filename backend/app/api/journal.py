"""
Trade Journal API — يومية التداول الشخصية
CRUD + إحصائيات
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.trade_journal import TradeJournalEntry, TradeDirection, TradeResult
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class JournalIn(BaseModel):
    symbol:       str
    direction:    str                  # BUY | SELL
    entry_price:  Optional[float] = None
    exit_price:   Optional[float] = None
    stop_loss:    Optional[float] = None
    take_profit:  Optional[float] = None
    lot_size:     Optional[float] = None
    pnl_pips:     Optional[float] = None
    pnl_usd:      Optional[float] = None
    result:       Optional[str]   = "OPEN"   # OPEN | WIN | LOSS | BE
    notes:        Optional[str]   = None
    strategy:     Optional[str]   = None
    timeframe:    Optional[str]   = None
    opened_at:    Optional[str]   = None     # ISO string
    closed_at:    Optional[str]   = None


class JournalUpdateIn(BaseModel):
    exit_price:  Optional[float] = None
    pnl_pips:    Optional[float] = None
    pnl_usd:     Optional[float] = None
    result:      Optional[str]   = None
    notes:       Optional[str]   = None
    strategy:    Optional[str]   = None
    closed_at:   Optional[str]   = None


def _entry_dict(e: TradeJournalEntry) -> dict:
    return {
        "id":          e.id,
        "symbol":      e.symbol,
        "direction":   e.direction,
        "result":      e.result,
        "entry_price": e.entry_price,
        "exit_price":  e.exit_price,
        "stop_loss":   e.stop_loss,
        "take_profit": e.take_profit,
        "lot_size":    e.lot_size,
        "pnl_pips":    e.pnl_pips,
        "pnl_usd":     e.pnl_usd,
        "notes":       e.notes,
        "strategy":    e.strategy,
        "timeframe":   e.timeframe,
        "opened_at":   e.opened_at.isoformat() if e.opened_at else None,
        "closed_at":   e.closed_at.isoformat() if e.closed_at else None,
        "created_at":  e.created_at.isoformat() if e.created_at else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
def list_entries(
    skip:    int   = 0,
    limit:   int   = 50,
    symbol:  str   = Query(default=""),
    result:  str   = Query(default=""),
    user:    User  = Depends(get_current_user),
    db:      Session = Depends(get_db),
):
    q = db.query(TradeJournalEntry).filter(TradeJournalEntry.user_id == user.id)
    if symbol: q = q.filter(TradeJournalEntry.symbol == symbol.upper())
    if result: q = q.filter(TradeJournalEntry.result == result.upper())
    total   = q.count()
    entries = q.order_by(TradeJournalEntry.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "entries": [_entry_dict(e) for e in entries]}


@router.post("")
def create_entry(
    data: JournalIn,
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    try:
        direction = TradeDirection(data.direction.upper())
        result    = TradeResult(data.result.upper() if data.result else "OPEN")
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    entry = TradeJournalEntry(
        user_id     = user.id,
        symbol      = data.symbol.upper(),
        direction   = direction,
        result      = result,
        entry_price = data.entry_price,
        exit_price  = data.exit_price,
        stop_loss   = data.stop_loss,
        take_profit = data.take_profit,
        lot_size    = data.lot_size,
        pnl_pips    = data.pnl_pips,
        pnl_usd     = data.pnl_usd,
        notes       = data.notes,
        strategy    = data.strategy,
        timeframe   = data.timeframe,
        opened_at   = datetime.fromisoformat(data.opened_at) if data.opened_at else datetime.now(timezone.utc),
        closed_at   = datetime.fromisoformat(data.closed_at) if data.closed_at else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_dict(entry)


@router.put("/{entry_id}")
def update_entry(
    entry_id: int,
    data: JournalUpdateIn,
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    entry = db.query(TradeJournalEntry).filter(
        TradeJournalEntry.id == entry_id,
        TradeJournalEntry.user_id == user.id,
    ).first()
    if not entry:
        raise HTTPException(404, "Entry not found")

    if data.exit_price  is not None: entry.exit_price  = data.exit_price
    if data.pnl_pips    is not None: entry.pnl_pips    = data.pnl_pips
    if data.pnl_usd     is not None: entry.pnl_usd     = data.pnl_usd
    if data.notes       is not None: entry.notes       = data.notes
    if data.strategy    is not None: entry.strategy    = data.strategy
    if data.closed_at   is not None: entry.closed_at   = datetime.fromisoformat(data.closed_at)
    if data.result:
        try:
            entry.result = TradeResult(data.result.upper())
        except ValueError:
            pass
        if entry.result != TradeResult.OPEN and not entry.closed_at:
            entry.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(entry)
    return _entry_dict(entry)


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: int,
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    entry = db.query(TradeJournalEntry).filter(
        TradeJournalEntry.id == entry_id,
        TradeJournalEntry.user_id == user.id,
    ).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/stats")
def get_stats(
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    entries = db.query(TradeJournalEntry).filter(
        TradeJournalEntry.user_id == user.id
    ).all()

    closed  = [e for e in entries if e.result != TradeResult.OPEN]
    wins    = [e for e in closed  if e.result == TradeResult.WIN]
    losses  = [e for e in closed  if e.result == TradeResult.LOSS]
    be      = [e for e in closed  if e.result == TradeResult.BE]
    open_t  = [e for e in entries if e.result == TradeResult.OPEN]

    win_rate   = round(len(wins) / len(closed) * 100, 1) if closed else 0
    total_pnl  = sum(e.pnl_usd or 0 for e in entries)
    avg_win    = sum(e.pnl_usd or 0 for e in wins)   / len(wins)   if wins   else 0
    avg_loss   = sum(e.pnl_usd or 0 for e in losses) / len(losses) if losses else 0

    # Best market
    sym_wins = {}
    for e in wins:
        sym_wins[e.symbol] = sym_wins.get(e.symbol, 0) + 1
    best_market = max(sym_wins, key=sym_wins.get) if sym_wins else None

    return {
        "total":       len(entries),
        "open":        len(open_t),
        "closed":      len(closed),
        "wins":        len(wins),
        "losses":      len(losses),
        "be":          len(be),
        "win_rate":    win_rate,
        "total_pnl":   round(total_pnl, 2),
        "avg_win":     round(avg_win,  2),
        "avg_loss":    round(avg_loss, 2),
        "best_market": best_market,
    }
