"""
Mosh AI Pro v5 - Strategy Builder API
CRUD for user-defined strategies + real evaluation against the live
AI engine (ai_engine_v5) + real Telegram test-alert sending.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from loguru import logger

from app.database import get_db
from app.services.auth_service import get_current_user, check_subscription
from app.models.user import User, UserRole, PlanType
from app.models.strategy import (
    Strategy, StrategyGroup, StrategyCondition, StrategyTriggerEvent,
    StrategyStatus, GroupLogic,
)
from app.services.strategy_engine import (
    evaluate_strategy, build_telegram_message, SUPPORTED_CONDITION_TYPES,
)

router = APIRouter()


def _require_paid(user: User, db: Session):
    """Strategy Builder actions (save/activate/duplicate/delete/telegram-test)
    are exclusive to active weekly/monthly subscribers. Trial users can browse
    and simulate, but not persist or trigger real alerts."""
    if user.role == UserRole.ADMIN:
        return
    check_subscription(user, db)  # downgrades an expired sub back to TRIAL as a side effect
    if user.plan not in (PlanType.WEEKLY, PlanType.MONTHLY):
        raise HTTPException(403, "هذه الميزة حصرية للمشتركين — اشترك لتفعيل استراتيجياتك الحقيقية")

# نفس مجموعة الرموز الثمانية بالـ Prototype (SYMBOL_POOL بالفرونت)
SIM_SYMBOLS = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD", "ETH/USD", "NAS100", "US30", "USOIL"]


def _norm_symbol(sym: str) -> str:
    return sym.replace("/", "").upper()


def _norm_timeframe(tf: str) -> str:
    return (tf or "1h").lower()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ConditionIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    groupId: str
    catId: str
    type: str
    label: str
    timeframe: str = "15m"
    tfMode: str = "نفس الفريم"
    value: str = ""
    weight: int = 10
    enabled: bool = True
    not_: bool = Field(False, alias="not")


class GroupIn(BaseModel):
    id: str
    name: str
    logic: str = "AND"
    atLeast: int = 1


class StrategyIn(BaseModel):
    name: str
    symbols: List[str] = []
    timeframes: List[str] = []
    minScore: int = 70
    triggerActions: Dict[str, bool] = {}
    execCfg: Dict[str, str] = {}
    tgChannel: Optional[str] = None
    tgFields: Dict[str, bool] = {}
    groups: List[GroupIn] = []
    conditions: List[ConditionIn] = []


class StatusIn(BaseModel):
    status: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_owned(db: Session, strategy_id: int, user) -> Strategy:
    s = db.query(Strategy).filter(Strategy.id == strategy_id, Strategy.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "الاستراتيجية غير موجودة")
    return s


def _apply_payload(db: Session, strategy: Strategy, body: StrategyIn):
    strategy.name       = body.name.strip() or "استراتيجية بدون اسم"
    strategy.symbols    = body.symbols
    strategy.timeframes = body.timeframes
    strategy.min_score  = body.minScore

    strategy.trigger_create_signal = body.triggerActions.get("createSignal", True)
    strategy.trigger_send_telegram = body.triggerActions.get("sendTelegram", True)
    strategy.trigger_monitor_entry = body.triggerActions.get("monitorEntry", True)

    strategy.exec_entry_type = body.execCfg.get("entry", "Market")
    strategy.exec_sl_type    = body.execCfg.get("sl", "Below Swing Low")
    strategy.exec_tp_type    = body.execCfg.get("tp", "Risk/Reward")
    try:
        strategy.exec_rr = float(body.execCfg.get("rr", 2) or 2)
    except (TypeError, ValueError):
        strategy.exec_rr = 2.0

    strategy.tg_chat_override  = body.tgChannel or None
    strategy.tg_send_entry      = body.tgFields.get("entry", True)
    strategy.tg_send_sl         = body.tgFields.get("sl", True)
    strategy.tg_send_tp         = body.tgFields.get("tp", True)
    strategy.tg_send_rr         = body.tgFields.get("rr", True)
    strategy.tg_send_confidence = body.tgFields.get("confidence", True)
    strategy.tg_send_conditions = body.tgFields.get("conditions", True)
    strategy.tg_send_chart      = body.tgFields.get("chart", False)

    db.flush()

    # استبدال كامل للمجموعات/الشروط — أبسط وأضمن من diffing
    for g in list(strategy.groups):
        db.delete(g)
    db.flush()

    by_group: Dict[str, List[ConditionIn]] = {}
    for c in body.conditions:
        by_group.setdefault(c.groupId, []).append(c)

    for gi, g in enumerate(body.groups):
        try:
            logic = GroupLogic(g.logic)
        except ValueError:
            logic = GroupLogic.AND
        group = StrategyGroup(
            strategy_id=strategy.id, name=g.name.strip() or f"مجموعة {gi+1}",
            logic=logic, at_least=max(1, g.atLeast), sort_order=gi,
        )
        db.add(group)
        db.flush()
        for ci, c in enumerate(by_group.get(g.id, [])):
            db.add(StrategyCondition(
                group_id=group.id, category=c.catId, type=c.type, label=c.label,
                timeframe=c.timeframe, tf_mode=c.tfMode, value=c.value,
                weight=c.weight, enabled=c.enabled, negate=c.not_, sort_order=ci,
            ))


def _serialize_full(s: Strategy) -> dict:
    groups_out, conditions_out = [], []
    for g in s.groups:
        gid = f"g{g.id}"
        groups_out.append({
            "id": gid, "name": g.name, "logic": g.logic.value,
            "atLeast": g.at_least, "collapsed": False,
        })
        for c in g.conditions:
            conditions_out.append({
                "id": f"c{c.id}", "groupId": gid, "catId": c.category, "type": c.type,
                "label": c.label, "timeframe": c.timeframe, "tfMode": c.tf_mode,
                "value": c.value or "", "weight": c.weight, "enabled": c.enabled,
                "not": c.negate,
            })
    return {
        "id": s.id, "name": s.name, "symbols": s.symbols or [], "timeframes": s.timeframes or [],
        "minScore": s.min_score,
        "triggerActions": {
            "createSignal": s.trigger_create_signal, "sendTelegram": s.trigger_send_telegram,
            "monitorEntry": s.trigger_monitor_entry,
        },
        "execCfg": {
            "entry": s.exec_entry_type, "sl": s.exec_sl_type, "tp": s.exec_tp_type,
            "rr": str(s.exec_rr),
        },
        "tgChannel": s.tg_chat_override or "",
        "tgFields": {
            "entry": s.tg_send_entry, "sl": s.tg_send_sl, "tp": s.tg_send_tp, "rr": s.tg_send_rr,
            "confidence": s.tg_send_confidence, "conditions": s.tg_send_conditions,
            "chart": s.tg_send_chart,
        },
        "status": s.status.value,
        "groups": groups_out,
        "conditions": conditions_out,
    }


def _serialize_summary(db: Session, s: Strategy) -> dict:
    conditions_count = sum(len(g.conditions) for g in s.groups)
    schools = {c.category for g in s.groups for c in g.conditions}
    signals_count = db.query(StrategyTriggerEvent).filter(
        StrategyTriggerEvent.strategy_id == s.id, StrategyTriggerEvent.triggered == True,
    ).count()
    return {
        "id": s.id, "name": s.name, "symbol": (s.symbols or ["-"])[0] if s.symbols else "-",
        "timeframe": (s.timeframes or ["-"])[-1].upper() if s.timeframes else "-",
        "confidence": s.min_score, "conditions": conditions_count, "schools": len(schools),
        "status": s.status.value,
        "lastTrigger": s.last_triggered_at.strftime("%Y-%m-%d %H:%M") if s.last_triggered_at else "لم يُشغّل بعد",
        "signals": signals_count,
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_strategies(db: Session = Depends(get_db), user = Depends(get_current_user)):
    rows = db.query(Strategy).filter(Strategy.user_id == user.id).order_by(Strategy.created_at.desc()).all()
    return {"strategies": [_serialize_summary(db, s) for s in rows]}


@router.post("")
def create_strategy(body: StrategyIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    if not body.name.strip():
        raise HTTPException(400, "اسم الاستراتيجية مطلوب")
    s = Strategy(user_id=user.id, name=body.name.strip(), status=StrategyStatus.DRAFT)
    db.add(s)
    db.flush()
    _apply_payload(db, s, body)
    db.commit()
    db.refresh(s)
    return _serialize_full(s)


@router.get("/{strategy_id}")
def get_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    return _serialize_full(_get_owned(db, strategy_id, user))


@router.put("/{strategy_id}")
def update_strategy(strategy_id: int, body: StrategyIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    s = _get_owned(db, strategy_id, user)
    _apply_payload(db, s, body)
    db.commit()
    db.refresh(s)
    return _serialize_full(s)


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    s = _get_owned(db, strategy_id, user)
    db.delete(s)
    db.commit()
    return {"success": True}


@router.post("/{strategy_id}/duplicate")
def duplicate_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    s = _get_owned(db, strategy_id, user)
    clone = Strategy(
        user_id=user.id, name=f"{s.name} (نسخة)", symbols=s.symbols, timeframes=s.timeframes,
        min_score=s.min_score,
        trigger_create_signal=s.trigger_create_signal, trigger_send_telegram=s.trigger_send_telegram,
        trigger_monitor_entry=s.trigger_monitor_entry,
        exec_entry_type=s.exec_entry_type, exec_sl_type=s.exec_sl_type, exec_tp_type=s.exec_tp_type,
        exec_rr=s.exec_rr, tg_chat_override=s.tg_chat_override,
        tg_send_entry=s.tg_send_entry, tg_send_sl=s.tg_send_sl, tg_send_tp=s.tg_send_tp,
        tg_send_rr=s.tg_send_rr, tg_send_confidence=s.tg_send_confidence,
        tg_send_conditions=s.tg_send_conditions, tg_send_chart=s.tg_send_chart,
        status=StrategyStatus.DRAFT,
    )
    db.add(clone)
    db.flush()
    for gi, g in enumerate(s.groups):
        ng = StrategyGroup(strategy_id=clone.id, name=g.name, logic=g.logic, at_least=g.at_least, sort_order=gi)
        db.add(ng)
        db.flush()
        for ci, c in enumerate(g.conditions):
            db.add(StrategyCondition(
                group_id=ng.id, category=c.category, type=c.type, label=c.label,
                timeframe=c.timeframe, tf_mode=c.tf_mode, value=c.value, weight=c.weight,
                enabled=c.enabled, negate=c.negate, sort_order=ci,
            ))
    db.commit()
    db.refresh(clone)
    return _serialize_full(clone)


@router.put("/{strategy_id}/status")
def set_status(strategy_id: int, body: StatusIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    s = _get_owned(db, strategy_id, user)
    try:
        s.status = StrategyStatus(body.status)
    except ValueError:
        raise HTTPException(400, "حالة غير صحيحة")
    db.commit()
    return {"success": True, "status": s.status.value}


# ─── Evaluation (real Simulation) ──────────────────────────────────────────────

async def _run_evaluation(db: Session, groups, conditions, min_score: int) -> List[dict]:
    from app.services.ai_engine_v5 import mosh_ai_engine_v5

    timeframe_candidates = sorted({c.timeframe for c in conditions if c.enabled}) or ["15m"]
    tf = _norm_timeframe(timeframe_candidates[-1])

    async def _one(symbol: str) -> dict:
        try:
            analysis = await mosh_ai_engine_v5.analyze_market(_norm_symbol(symbol), tf)
        except Exception as e:
            logger.warning(f"Strategy evaluation failed for {symbol}/{tf}: {e}")
            return {"symbol": symbol, "error": "تعذّر تحليل هذا الرمز الآن"}
        result = evaluate_strategy(groups, conditions, analysis, min_score, price=analysis.get("current_price"))
        return {
            "symbol": symbol, "price": result["price"], "score": result["score"],
            "triggered": result["triggered"], "matched": result["matched"],
            "unsupported": result["unsupported"],
        }

    return list(await asyncio.gather(*[_one(sym) for sym in SIM_SYMBOLS]))


def _flat_conditions(s: Strategy) -> List[StrategyCondition]:
    return [c for g in s.groups for c in g.conditions]


@router.post("/{strategy_id}/evaluate")
async def evaluate_saved(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    s = _get_owned(db, strategy_id, user)
    if not _flat_conditions(s):
        raise HTTPException(400, "أضف شروطًا للاستراتيجية أولًا")
    results = await _run_evaluation(db, s.groups, _flat_conditions(s), s.min_score)
    return {"results": results}


@router.post("/evaluate-preview")
async def evaluate_preview(body: StrategyIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """يسمح بتجربة الاستراتيجية قبل الحفظ — نفس محرك التقييم الحقيقي، بدون تخزين."""
    if not body.conditions:
        raise HTTPException(400, "أضف شروطًا للاستراتيجية أولًا")

    class _FakeGroup:
        def __init__(self, g: GroupIn):
            self.id = g.id
            try:
                self.logic = GroupLogic(g.logic)
            except ValueError:
                self.logic = GroupLogic.AND
            self.at_least = max(1, g.atLeast)

    class _FakeCondition:
        def __init__(self, c: ConditionIn):
            self.id = c.id
            self.group_id = c.groupId
            self.type = c.type
            self.label = c.label
            self.timeframe = c.timeframe
            self.value = c.value
            self.weight = c.weight
            self.enabled = c.enabled
            self.negate = c.not_

    fake_groups = [_FakeGroup(g) for g in body.groups]
    fake_conditions = [_FakeCondition(c) for c in body.conditions]
    results = await _run_evaluation(db, fake_groups, fake_conditions, body.minScore)
    return {"results": results}


@router.get("/{strategy_id}/events")
def list_events(strategy_id: int, limit: int = 20, db: Session = Depends(get_db), user = Depends(get_current_user)):
    s = _get_owned(db, strategy_id, user)
    events = (
        db.query(StrategyTriggerEvent)
        .filter(StrategyTriggerEvent.strategy_id == s.id)
        .order_by(StrategyTriggerEvent.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return {
        "status": s.status.value,
        "lastTrigger": s.last_triggered_at.isoformat() if s.last_triggered_at else None,
        "events": [
            {
                "id": e.id, "symbol": e.symbol, "timeframe": e.timeframe, "score": e.score,
                "triggered": e.triggered, "price": e.price, "telegramSent": e.telegram_sent,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# ─── Telegram test alert (real send, no mock) ──────────────────────────────────

@router.post("/{strategy_id}/telegram/test")
async def send_test_alert(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    _require_paid(user, db)
    s = _get_owned(db, strategy_id, user)
    if not user.telegram_id:
        raise HTTPException(400, "اربط حساب Telegram أولاً من صفحة الملف الشخصي قبل إرسال تنبيه تجريبي")

    from app.services.admin_notify import get_bot_token
    import aiohttp

    token = get_bot_token()
    if not token:
        raise HTTPException(500, "توكن بوت Telegram غير مضبوط بالمنصة")

    symbol = (s.symbols or ["XAU/USD"])[0]
    tf = _norm_timeframe((s.timeframes or ["15m"])[-1])

    from app.services.ai_engine_v5 import mosh_ai_engine_v5
    conditions = _flat_conditions(s)
    if not conditions:
        raise HTTPException(400, "أضف شروطًا للاستراتيجية أولًا")

    analysis = await mosh_ai_engine_v5.analyze_market(_norm_symbol(symbol), tf)
    result = evaluate_strategy(s.groups, conditions, analysis, s.min_score, price=analysis.get("current_price"))
    text = "🧪 [رسالة تجريبية]\n" + build_telegram_message(s, result, symbol, tf, analysis)

    chat_id = s.tg_chat_override or user.telegram_id
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with aiohttp.ClientSession() as sess:
        resp = await sess.post(url, json={"chat_id": chat_id, "text": text}, timeout=aiohttp.ClientTimeout(total=10))
        if resp.status != 200:
            body_text = await resp.text()
            logger.warning(f"Telegram test alert failed: {body_text}")
            raise HTTPException(502, "تعذّر إرسال الرسالة عبر Telegram — تحقق من الربط والتوكن")

    return {"success": True, "message": "تم إرسال تنبيه تجريبي حقيقي ✅"}
