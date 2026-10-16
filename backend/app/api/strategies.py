"""
Mosh AI Pro v5 - Strategy Builder API
CRUD for user-defined strategies + real evaluation against the live
AI engine (ai_engine_v5) + real Telegram test-alert sending.
"""
import asyncio
from datetime import datetime, timezone, timedelta
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
    distinct_timeframes, primary_timeframe, norm_timeframe,
)
from app.services.strategy_access import (
    access_tier as _access_tier,
    LIMITED_MAX_STRATEGIES, LIMITED_MAX_SYMBOLS,
)

router = APIRouter()


def _enforce_limited_constraints(db: Session, user: User, body: "StrategyIn", exclude_strategy_id: int = None):
    """يرفع 403 عند تجاوز قيود الفئة المحدودة. exclude_strategy_id: استبعاد
    الاستراتيجية الحالية من عدّ 'واحدة فقط' عند التعديل، لا الإنشاء."""
    q = db.query(Strategy).filter(Strategy.user_id == user.id)
    if exclude_strategy_id is not None:
        q = q.filter(Strategy.id != exclude_strategy_id)
    if q.count() >= LIMITED_MAX_STRATEGIES:
        raise HTTPException(403, "التجربة المحدودة تسمح باستراتيجية واحدة فقط — رقّي لباقة Premium لإنشاء المزيد")

    if len([x for x in (body.symbols or []) if x]) > LIMITED_MAX_SYMBOLS:
        raise HTTPException(403, "التجربة تسمح برمز واحد فقط للاستراتيجية — رقّي لباقة Premium لمراقبة عدة رموز")

# نفس مجموعة الرموز الثمانية بالـ Prototype (SYMBOL_POOL بالفرونت)
SIM_SYMBOLS = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD", "ETH/USD", "NAS100", "US30", "USOIL"]


def _norm_symbol(sym: str) -> str:
    return sym.replace("/", "").upper()




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
    if _access_tier(user, db) == "limited":
        _enforce_limited_constraints(db, user, body)
    if not body.name.strip():
        raise HTTPException(400, "اسم الاستراتيجية مطلوب")
    s = Strategy(user_id=user.id, name=body.name.strip(), status=StrategyStatus.DRAFT)
    db.add(s)
    db.flush()
    _apply_payload(db, s, body)
    db.commit()
    db.refresh(s)
    return _serialize_full(s)


# ─── مكتبة الاستراتيجيات الجاهزة (2026-10-14) ──────────────────────────────────
# ⚠️ قبل "/{strategy_id}" عمداً — وإلا التقطه ذلك المسار ("templates" ليس رقماً ← 422).

@router.get("/templates")
def list_templates(user = Depends(get_current_user)):
    from app.services.strategy_templates import all_templates
    return {"templates": all_templates()}


@router.post("/templates/{key}/copy")
def copy_template(key: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """ينشئ نسخة خاصة بالعميل (DRAFT) — يعدّلها ويفعّلها كأي استراتيجية؛ القالب نفسه لا يتغيّر."""
    from app.services.strategy_templates import get_template
    t = get_template(key)
    if not t:
        raise HTTPException(404, "القالب غير موجود")
    groups, conds = [], []
    for gi, g in enumerate(t["groups"], 1):
        gid = f"tg{gi}"
        groups.append(GroupIn(id=gid, name=g["name"], logic=g["logic"], atLeast=g["atLeast"]))
        for ci, c in enumerate(g["conditions"], 1):
            conds.append(ConditionIn(id=f"tc{gi}_{ci}", groupId=gid, catId=c["catId"], type=c["type"],
                                     label=c["label"], timeframe=c["timeframe"], value=c["value"],
                                     weight=c["weight"]))
    body = StrategyIn(
        name=t["name_ar"], symbols=t["symbols"], timeframes=t["timeframes"], minScore=t["min_score"],
        triggerActions={"createSignal": True, "sendTelegram": True, "monitorEntry": True},
        execCfg=t["exec"], groups=groups, conditions=conds,
    )
    if _access_tier(user, db) == "limited":
        _enforce_limited_constraints(db, user, body)
    s = Strategy(user_id=user.id, name=body.name, status=StrategyStatus.DRAFT)
    db.add(s)
    db.flush()
    _apply_payload(db, s, body)
    from app.models.strategy_backtest import StrategyTemplateCopy
    db.add(StrategyTemplateCopy(template_key=key, strategy_id=s.id, user_id=user.id))
    db.commit()
    db.refresh(s)
    logger.info(f"📚 Template {key} v{t['version']} copied → strategy #{s.id} (user {user.id})")
    return _serialize_full(s)


@router.get("/{strategy_id}")
def get_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    return _serialize_full(_get_owned(db, strategy_id, user))


@router.put("/{strategy_id}")
def update_strategy(strategy_id: int, body: StrategyIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if _access_tier(user, db) == "limited":
        _enforce_limited_constraints(db, user, body, exclude_strategy_id=strategy_id)
    s = _get_owned(db, strategy_id, user)
    _apply_payload(db, s, body)
    db.commit()
    db.refresh(s)
    return _serialize_full(s)


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    # الحذف متاح لأي مالك بغض النظر عن الفئة — الفئة المحدودة محتاجة تقدر
    # تحذف استراتيجيتها الوحيدة لتبني غيرها (سقف "واحدة فقط" بالحفظ لا الحذف).
    s = _get_owned(db, strategy_id, user)
    db.delete(s)
    db.commit()
    return {"success": True}


@router.post("/{strategy_id}/duplicate")
def duplicate_strategy(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if _access_tier(user, db) == "limited" and db.query(Strategy).filter(Strategy.user_id == user.id).count() >= LIMITED_MAX_STRATEGIES:
        raise HTTPException(403, "التجربة المحدودة تسمح باستراتيجية واحدة فقط — رقّي لباقة Premium لإنشاء المزيد")
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
    # لا قيد تفعيل إضافي هون — التزام الفئة المحدودة (عدد/شروط) يُفرَض
    # وقت الحفظ أعلاه، فالاستراتيجية المحفوظة مطابقة أصلاً حين تصل هون.
    s = _get_owned(db, strategy_id, user)
    try:
        s.status = StrategyStatus(body.status)
    except ValueError:
        raise HTTPException(400, "حالة غير صحيحة")
    db.commit()
    return {"success": True, "status": s.status.value}


# ─── Backtest (2026-10-14) ─────────────────────────────────────────────────────

class BacktestIn(BaseModel):
    days: int = 30
    symbols: List[str] = []


_BACKTEST_TASKS: set = set()
BACKTESTS_PER_DAY = 10


def _bt_out(bt) -> dict:
    return {"id": bt.id, "status": bt.status, "progress": bt.progress, "params": bt.params,
            "result": bt.result, "error": bt.error,
            "created_at": bt.created_at.isoformat() if bt.created_at else None,
            "finished_at": bt.finished_at.isoformat() if bt.finished_at else None}


@router.post("/{strategy_id}/backtest")
async def start_backtest(strategy_id: int, body: BacktestIn, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """يبدأ باكتيست بالخلفية (يأخذ دقائق) — راجع app/services/strategy_backtest.py لطريقة الحساب."""
    from app.models.strategy_backtest import StrategyBacktest
    from app.services.strategy_backtest import run_backtest_job
    s = _get_owned(db, strategy_id, user)
    if not any(c.enabled for g in s.groups for c in g.conditions):
        raise HTTPException(400, "أضف شروطاً مفعّلة واحفظ الاستراتيجية أولاً")
    running = db.query(StrategyBacktest).filter(
        StrategyBacktest.user_id == user.id, StrategyBacktest.status.in_(["queued", "running"])).first()
    if running:
        raise HTTPException(409, "عندك باكتيست قيد التشغيل — انتظر حتى ينتهي")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    if db.query(StrategyBacktest).filter(StrategyBacktest.user_id == user.id,
                                         StrategyBacktest.created_at >= since).count() >= BACKTESTS_PER_DAY:
        raise HTTPException(429, f"الحد {BACKTESTS_PER_DAY} اختبارات يومياً — جرّب غداً")
    days = max(3, min(int(body.days or 30), 300))
    cap = LIMITED_MAX_SYMBOLS if _access_tier(user, db) == "limited" else 3
    symbols = [x for x in (body.symbols or s.symbols or []) if x][:cap] or ["XAU/USD"]
    bt = StrategyBacktest(strategy_id=s.id, user_id=user.id, status="queued", progress=0,
                          params={"days": days, "symbols": symbols})
    db.add(bt)
    db.commit()
    db.refresh(bt)
    task = asyncio.get_running_loop().create_task(run_backtest_job(bt.id))
    _BACKTEST_TASKS.add(task)
    task.add_done_callback(_BACKTEST_TASKS.discard)
    return _bt_out(bt)


@router.get("/{strategy_id}/backtest")
def latest_backtest(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    from app.models.strategy_backtest import StrategyBacktest
    _get_owned(db, strategy_id, user)
    bt = (db.query(StrategyBacktest).filter(StrategyBacktest.strategy_id == strategy_id)
            .order_by(StrategyBacktest.id.desc()).first())
    return _bt_out(bt) if bt else {"status": "none"}


# ─── Evaluation (real Simulation) ──────────────────────────────────────────────

async def _run_evaluation(db: Session, groups, conditions, min_score: int, symbols: List[str]) -> List[dict]:
    from app.services.ai_engine_v5 import mosh_ai_engine_v5

    # يفحص الرموز اللي اختارها المستخدم فعليًا بالاستراتيجية — لا فائدة من
    # محاكاة استراتيجية مبنية على ARAMCO مقابل مجموعة أسواق فوركس ثابتة.
    scan_symbols = symbols or SIM_SYMBOLS

    # (2026-09-06) كل شرط له فريمه الخاص — نجيب تحليل حقيقي مستقل لكل فريم
    # فريد مستخدم فعليًا (عبر analyze_market_multi_tf)، لا فريم واحد مُختار
    # اعتباطيًا لكل الاستراتيجية.
    tfs = distinct_timeframes(conditions)
    primary_tf = primary_timeframe(conditions)

    async def _one(symbol: str) -> dict:
        try:
            analyses = await mosh_ai_engine_v5.analyze_market_multi_tf(_norm_symbol(symbol), tfs)
        except Exception as e:
            logger.warning(f"Strategy evaluation failed for {symbol}/{tfs}: {e}")
            return {"symbol": symbol, "error": "تعذّر تحليل هذا الرمز الآن"}
        primary_analysis = analyses.get(primary_tf) or next(iter(analyses.values()), {})
        result = evaluate_strategy(groups, conditions, analyses, min_score, price=primary_analysis.get("current_price"))
        return {
            "symbol": symbol, "price": result["price"], "score": result["score"],
            "triggered": result["triggered"], "matched": result["matched"],
            "unsupported": result["unsupported"],
        }

    return list(await asyncio.gather(*[_one(sym) for sym in scan_symbols]))


def _flat_conditions(s: Strategy) -> List[StrategyCondition]:
    return [c for g in s.groups for c in g.conditions]


@router.post("/{strategy_id}/evaluate")
async def evaluate_saved(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    s = _get_owned(db, strategy_id, user)
    if not _flat_conditions(s):
        raise HTTPException(400, "أضف شروطًا للاستراتيجية أولًا")
    results = await _run_evaluation(db, s.groups, _flat_conditions(s), s.min_score, s.symbols or [])
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
    results = await _run_evaluation(db, fake_groups, fake_conditions, body.minScore, body.symbols or [])
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
                "diagnostics": e.diagnostics_json,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# ─── Telegram test alert (real send, no mock) ──────────────────────────────────

@router.post("/{strategy_id}/telegram/test")
async def send_test_alert(strategy_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    tier = _access_tier(user, db)
    if tier == "limited" and user.strategy_free_alerts_left <= 0:
        raise HTTPException(403, "استهلكت تنبيهاتك المجانية الثلاثة لباني الاستراتيجيات — رقّي لباقة Premium لتنبيهات غير محدودة")
    s = _get_owned(db, strategy_id, user)
    if not user.telegram_id:
        raise HTTPException(400, "اربط حساب Telegram أولاً من صفحة الملف الشخصي قبل إرسال تنبيه تجريبي")

    from app.services.admin_notify import get_bot_token
    import aiohttp

    token = get_bot_token()
    if not token:
        raise HTTPException(500, "توكن بوت Telegram غير مضبوط بالمنصة")

    symbol = (s.symbols or ["XAU/USD"])[0]

    from app.services.ai_engine_v5 import mosh_ai_engine_v5
    conditions = _flat_conditions(s)
    if not conditions:
        raise HTTPException(400, "أضف شروطًا للاستراتيجية أولًا")

    tfs = distinct_timeframes(conditions)
    primary_tf = primary_timeframe(conditions)
    analyses = await mosh_ai_engine_v5.analyze_market_multi_tf(_norm_symbol(symbol), tfs)
    primary_analysis = analyses.get(primary_tf) or next(iter(analyses.values()), {})
    result = evaluate_strategy(s.groups, conditions, analyses, s.min_score, price=primary_analysis.get("current_price"))
    # (2026-10-16) نفس مستويات التنبيه الحي (قواعد الباكتيست) — كي تشبه الرسالة التجريبية ما سيصل فعلاً
    from app.services.strategy_backtest import infer_side
    from app.services.strategy_checker import _alert_levels
    side = infer_side([c for c in conditions if c.enabled]) or \
        (primary_analysis.get("recommendation") if primary_analysis.get("recommendation") in ("BUY", "SELL") else None)
    if side:
        lv = await _alert_levels(symbol, primary_tf, side, float(s.exec_rr or 2.0), primary_analysis.get("current_price"))
        if lv:
            primary_analysis = dict(primary_analysis, levels=lv)
    text = "🧪 [رسالة تجريبية]\n" + build_telegram_message(s, result, symbol, primary_tf, primary_analysis)

    chat_id = s.tg_chat_override or user.telegram_id
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with aiohttp.ClientSession() as sess:
        resp = await sess.post(url, json={"chat_id": chat_id, "text": text}, timeout=aiohttp.ClientTimeout(total=10))
        if resp.status != 200:
            body_text = await resp.text()
            logger.warning(f"Telegram test alert failed: {body_text}")
            raise HTTPException(502, "تعذّر إرسال الرسالة عبر Telegram — تحقق من الربط والتوكن")

    if tier == "limited":
        user.strategy_free_alerts_left = max(0, user.strategy_free_alerts_left - 1)
        db.commit()

    return {"success": True, "message": "تم إرسال تنبيه تجريبي حقيقي ✅"}
