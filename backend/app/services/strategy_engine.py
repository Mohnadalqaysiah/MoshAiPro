"""
Mosh AI Pro v5 - Strategy Builder Evaluation Engine
Maps user-defined strategy conditions to REAL fields computed by
ai_engine_v5.analyze_market() / ict_engine.full_analysis(). Any
condition type not in SUPPORTED_CONDITION_TYPES is honestly reported
as unsupported rather than silently guessed — never fabricate a match.
"""
import re
from typing import Any, Dict, List, Optional

_BULL_WORDS = ("صاعد", "شراء", "BULL", "BUY")
_BEAR_WORDS = ("هابط", "بيع", "BEAR", "SELL")


def _direction_hint(value: Optional[str]) -> Optional[str]:
    v = (value or "").strip().upper()
    if not v:
        return None
    if any(w in v for w in _BULL_WORDS):
        return "BULL"
    if any(w in v for w in _BEAR_WORDS):
        return "BEAR"
    return None


def _parse_numeric(value: Optional[str], actual: Optional[float]) -> Optional[bool]:
    """Parses a '<30' / '>=70' style comparison against a real numeric value."""
    if actual is None or not value:
        return None
    m = re.match(r"^\s*(<=|>=|<|>|=)\s*(-?\d+(?:\.\d+)?)\s*$", value.strip())
    if not m:
        return None
    op, num = m.group(1), float(m.group(2))
    if op == "<":  return actual < num
    if op == "<=": return actual <= num
    if op == ">":  return actual > num
    if op == ">=": return actual >= num
    return abs(actual - num) < 1e-9


# ─── SMC / ICT extractors ──────────────────────────────────────────────────

def _ext_bos(a: Dict, value: Optional[str]) -> Optional[bool]:
    events = ((a.get("market_structure") or {}).get("bos_events")) or []
    hint = _direction_hint(value)
    if hint == "BULL": return any(e.get("type") == "BULLISH_BOS" for e in events)
    if hint == "BEAR": return any(e.get("type") == "BEARISH_BOS" for e in events)
    return len(events) > 0


def _ext_choch(a: Dict, value: Optional[str]) -> Optional[bool]:
    events = ((a.get("market_structure") or {}).get("choch_events")) or []
    hint = _direction_hint(value)
    if hint == "BULL": return any(e.get("type") == "BULLISH_CHOCH" for e in events)
    if hint == "BEAR": return any(e.get("type") == "BEARISH_CHOCH" for e in events)
    return len(events) > 0


def _ext_ob(a: Dict, value: Optional[str]) -> Optional[bool]:
    ob = a.get("order_blocks") or {}
    hint = _direction_hint(value)
    if hint == "BULL": return bool(ob.get("in_bullish_ob") or ob.get("nearest_bullish"))
    if hint == "BEAR": return bool(ob.get("in_bearish_ob") or ob.get("nearest_bearish"))
    return bool(ob.get("in_bullish_ob") or ob.get("in_bearish_ob"))


def _ext_fvg(a: Dict, value: Optional[str]) -> Optional[bool]:
    fvg = a.get("fvg") or {}
    hint = _direction_hint(value)
    if hint == "BULL": return bool(fvg.get("in_bullish_fvg"))
    if hint == "BEAR": return bool(fvg.get("in_bearish_fvg"))
    return bool(fvg.get("in_bullish_fvg") or fvg.get("in_bearish_fvg"))


def _ext_liquidity_sweep(a: Dict, value: Optional[str]) -> Optional[bool]:
    sweep = a.get("liquidity_sweep") or {}
    hint = _direction_hint(value)
    if hint == "BULL": return bool(sweep.get("has_bullish_sweep"))
    if hint == "BEAR": return bool(sweep.get("has_bearish_sweep"))
    return bool(sweep.get("has_bullish_sweep") or sweep.get("has_bearish_sweep"))


def _ext_equal_highs(a: Dict, value: Optional[str]) -> Optional[bool]:
    liq = a.get("liquidity") or {}
    return len(liq.get("equal_highs") or []) > 0


def _ext_equal_lows(a: Dict, value: Optional[str]) -> Optional[bool]:
    liq = a.get("liquidity") or {}
    return len(liq.get("equal_lows") or []) > 0


def _ext_premium_discount(a: Dict, value: Optional[str]) -> Optional[bool]:
    zone = ((a.get("premium_discount") or {}).get("zone") or "").upper()
    if not zone:
        return None
    v = (value or "").upper()
    if "DISCOUNT" in v or "خصم" in (value or ""):
        return "DISCOUNT" in zone
    if "PREMIUM" in v or "علاوة" in (value or ""):
        return "PREMIUM" in zone
    return zone != "EQUILIBRIUM"


def _ext_killzone(a: Dict, value: Optional[str]) -> Optional[bool]:
    kz = a.get("kill_zone") or {}
    if "is_kill_zone" not in kz:
        return None
    if value and ("مثالي" in value or "OPTIMAL" in value.upper()):
        return bool(kz.get("is_optimal_time"))
    return bool(kz.get("is_kill_zone"))


def _session_match(a: Dict, needle: str) -> Optional[bool]:
    kz = a.get("kill_zone") or {}
    session = kz.get("active_session")
    if session is None:
        return None
    return needle.upper() in str(session).upper()


# ─── Classic indicator extractors (from ict_engine's `indicators` dict) ───

def _ext_rsi(a: Dict, value: Optional[str]) -> Optional[bool]:
    rsi = (a.get("indicators") or {}).get("rsi")
    return _parse_numeric(value, rsi)


def _ext_stoch(a: Dict, value: Optional[str]) -> Optional[bool]:
    k = (a.get("indicators") or {}).get("stoch_k")
    return _parse_numeric(value, k)


def _ext_macd(a: Dict, value: Optional[str]) -> Optional[bool]:
    ind = a.get("indicators") or {}
    macd, sig = ind.get("macd"), ind.get("macd_signal")
    if macd is None or sig is None:
        return None
    parsed = _parse_numeric(value, macd)
    if parsed is not None:
        return parsed
    hint = _direction_hint(value)
    if hint == "BULL": return macd > sig
    if hint == "BEAR": return macd < sig
    if not value:
        return macd > sig   # default: bullish cross
    return None


def _ext_ema(a: Dict, value: Optional[str]) -> Optional[bool]:
    ind = a.get("indicators") or {}
    ema20, price = ind.get("ema_20"), a.get("current_price")
    if ema20 is None or price is None:
        return None
    parsed = _parse_numeric(value, ema20)
    if parsed is not None:
        return parsed
    hint = _direction_hint(value)
    if hint == "BULL": return price > ema20
    if hint == "BEAR": return price < ema20
    if not value:
        return price > ema20
    return None


def _ext_atr(a: Dict, value: Optional[str]) -> Optional[bool]:
    return _parse_numeric(value, a.get("atr"))


SUPPORTED_CONDITION_TYPES = {
    # ICT / SMC
    "bos":       _ext_bos,
    "choch":     _ext_choch,
    "ob":        _ext_ob,
    "fvg":       _ext_fvg,
    "liquidity": _ext_liquidity_sweep,
    "eqh":       _ext_equal_highs,
    "eql":       _ext_equal_lows,
    "premium":   _ext_premium_discount,
    "killzone":  _ext_killzone,
    # Sessions & Time
    "london":    lambda a, v: _session_match(a, "LONDON"),
    "newyork":   lambda a, v: _session_match(a, "NEW_YORK"),
    "asian":     lambda a, v: _session_match(a, "ASIA"),
    "killzones": _ext_killzone,
    # Technical Indicators
    "rsi":   _ext_rsi,
    "macd":  _ext_macd,
    "ema":   _ext_ema,
    "stoch": _ext_stoch,
    # Volatility
    "atrv": _ext_atr,
}


def evaluate_condition(condition, analysis: Dict) -> Optional[bool]:
    """Returns True/False if the condition type is supported and evaluable
    against `analysis` (the real analyze_market() output), or None if the
    condition type has no real implementation yet."""
    extractor = SUPPORTED_CONDITION_TYPES.get(condition.type)
    if not extractor:
        return None
    result = extractor(analysis, condition.value)
    if result is None:
        return None
    return (not result) if condition.negate else result


def evaluate_strategy(groups: List, conditions: List, analysis: Dict, min_score: int, price: Optional[float] = None) -> Dict:
    """Pure evaluation of a strategy's saved groups/conditions against one
    real analyze_market() result. Unsupported conditions never count as a
    match — they're surfaced separately in `unsupported` for UI honesty."""
    enabled = [c for c in conditions if c.enabled]

    hit_by_id: Dict[int, bool] = {}
    unsupported_ids = set()
    unsupported = []
    for c in enabled:
        raw = evaluate_condition(c, analysis)
        if raw is None:
            unsupported_ids.add(c.id)
            unsupported.append({"id": c.id, "type": c.type, "label": c.label})
            hit_by_id[c.id] = False
        else:
            hit_by_id[c.id] = raw

    score = min(100, sum(c.weight for c in enabled if hit_by_id.get(c.id)))

    # شروط غير مدعومة تُستثنى من منطق المجموعة (AND/OR/AT_LEAST) كليًا — لا
    # تُحتسب "متحققة" (ذلك تلفيق) ولا "غير متحققة" (ذلك يعطّل AND للأبد بسبب
    # نوع لم يُبنَ بعد). تبقى ظاهرة بـ matched/unsupported لشفافية الواجهة فقط.
    groups_with_members = [
        g for g in groups
        if any(c.group_id == g.id and c.id not in unsupported_ids for c in enabled)
    ]
    groups_passed = True
    for g in groups_with_members:
        members = [c for c in enabled if c.group_id == g.id and c.id not in unsupported_ids]
        hits = sum(1 for c in members if hit_by_id.get(c.id))
        if g.logic.value == "AND":
            ok = hits == len(members)
        elif g.logic.value == "OR":
            ok = hits > 0
        else:  # AT_LEAST
            ok = hits >= (g.at_least or 1)
        if not ok:
            groups_passed = False

    matched = [{"id": c.id, "label": c.label, "hit": hit_by_id.get(c.id, False)} for c in enabled]
    triggered = bool(groups_passed and score >= min_score and len(enabled) > 0)

    return {
        "score": score,
        "groups_passed": groups_passed,
        "matched": matched,
        "unsupported": unsupported,
        "triggered": triggered,
        "price": price,
    }


def build_telegram_message(strategy, eval_result: Dict, symbol: str, timeframe: str, analysis: Dict) -> str:
    """Mirrors the frontend's tgTemplate builder, using real evaluation data."""
    levels = analysis.get("levels") or {}
    rec = analysis.get("recommendation") or "WAIT"
    direction_line = "🟢 LONG" if rec == "BUY" else ("🔴 SHORT" if rec == "SELL" else "⚪ WAIT")

    lines = ["━━━━━━━━━━━━━━", "🔥 STRATEGY TRIGGERED", "", f"{strategy.name}", f"{symbol}", f"{timeframe}", "",
              "Direction:", direction_line]
    if strategy.tg_send_entry and levels.get("entry") is not None:
        lines += ["", "Entry:", f"{levels.get('entry')}"]
    if strategy.tg_send_sl and levels.get("stop_loss") is not None:
        lines += ["", "Stop Loss:", f"{levels.get('stop_loss')}"]
    if strategy.tg_send_tp and levels.get("tp1") is not None:
        lines += ["", "Take Profit:", f"{levels.get('tp1')}"]
    if strategy.tg_send_rr and levels.get("risk_reward") is not None:
        lines += ["", "RR:", f"1:{levels.get('risk_reward')}"]
    if strategy.tg_send_confidence:
        lines += ["", "Confidence:", f"{eval_result['score']}%"]
    if strategy.tg_send_conditions:
        lines += ["", "Signals:"]
        for m in eval_result["matched"][:6]:
            if m["hit"]:
                lines.append(f"✓ {m['label']}")
    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)
