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

# (2026-09-06) كل شرط عنده حقل timeframe خاص فيه بالواجهة (وكان محفوظ
# بقاعدة البيانات) — بس التقييم كان يتجاهله كليًا ويفحص كل الشروط على فريم
# واحد للاستراتيجية كلها، مُختار أبجديًا لا زمنيًا (مثلاً "1H" يسبق "1D"
# أبجديًا رغم إنه أصغر زمنيًا). الدوال هون تحسب الأطر الفريدة المستخدمة
# فعليًا وترتّبها زمنيًا صح، تمهيدًا لجلب تحليل حقيقي مستقل لكل فريم
# (عبر analyze_market_multi_tf) وتوجيه كل شرط لتحليل فريمه هو تحديدًا.
_TF_MINUTES = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
}


def norm_timeframe(tf: Optional[str]) -> str:
    return (tf or "15m").strip().lower()


def tf_minutes(tf: Optional[str]) -> int:
    return _TF_MINUTES.get(norm_timeframe(tf), 60)


def distinct_timeframes(conditions: List) -> List[str]:
    """كل الأطر الزمنية الفريدة المفعّلة بشروط الاستراتيجية، مرتّبة زمنيًا
    (الأصغر أولًا) — لا فرز أبجدي."""
    tfs = {norm_timeframe(c.timeframe) for c in conditions if c.enabled}
    return sorted(tfs, key=tf_minutes) or ["15m"]


def primary_timeframe(conditions: List) -> str:
    """الأصغر (الأكثر دقة) بين الأطر المستخدمة — فريم الدخول الفعلي عادة،
    بينما الأطر الأعلى تُستخدم كفلتر اتجاه/سياق. يُستخدم لعرض السعر
    والتوصية والمستويات برسالة التنبيه."""
    return distinct_timeframes(conditions)[0]


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


def _ext_direction(a: Dict, value: Optional[str]) -> Optional[bool]:
    """
    اتجاه الصفقة كما قرّره المحرك (BUY / SELL / WAIT).

    (2026-09-17) أُضيف بعد سؤال محقّ: «كيف تكون للشراء ووصلتني إشارات
    بيع؟». والسبب أن قراري الاستراتيجية والاتجاه **منفصلان تماماً**:
    شروط المستخدم تقرّر **هل** يُرسَل تنبيه، ومستويات المحرك تقرّر
    **باتجاه أي جهة** — ولا تتحدثان. فشرط مثل «منطقة خصم» يرجّح الشراء
    سياقياً ولا يمنع المحرك من حساب مستويات بيع على فريم أصغر.

    وبلا هذا الشرط لا يملك المستخدم أي وسيلة لتقييد الاتجاه، فيتلقى
    الجهتين مهما ضبط شروطه — وهو ما لا يمكن استنتاجه من الواجهة.

    القيم: شراء/buy/long أو بيع/sell/short. وبلا قيمة: أي اتجاه محسوم
    (أي ليس WAIT).
    """
    rec = (a.get("recommendation") or "").upper()
    if not rec:
        return None
    v = (value or "").strip()
    vu = v.upper()
    if any(w in vu for w in ("BUY", "LONG")) or any(w in v for w in ("شراء", "صعود")):
        return rec == "BUY"
    if any(w in vu for w in ("SELL", "SHORT")) or any(w in v for w in ("بيع", "هبوط")):
        return rec == "SELL"
    return rec in ("BUY", "SELL")


def _ext_killzone(a: Dict, value: Optional[str]) -> Optional[bool]:
    kz = a.get("kill_zone") or {}
    if "is_kill_zone" not in kz:
        return None
    if value and ("مثالي" in value or "OPTIMAL" in value.upper()):
        return bool(kz.get("is_optimal_time"))
    return bool(kz.get("is_kill_zone"))


# نوافذ الجلسات الكاملة بتوقيت UTC — وهي متداخلة بطبيعتها، فالسوق لا
# يسلّم من جلسة لأخرى بقطع.
_SESSION_WINDOWS = {
    "ASIA":     [(0, 9), (23, 24)],   # طوكيو/سيدني
    "LONDON":   [(7, 16)],
    "NEW_YORK": [(12, 21)],
}


def _session_match(a: Dict, needle: str) -> Optional[bool]:
    """
    هل نحن داخل الجلسة المطلوبة؟

    (2026-09-17) بلاغ حقيقي: استراتيجية بمجموعة «واحد على الأقل» تضم
    لندن ونيويورك وآسيا معاً سجّلت «تحقّق 0 من 3» الساعة 09:36 UTC —
    أي أن الجلسات الثلاث فشلت مجتمعةً في وقت لندن.

    السبب: كانت تُطابق `kill_zone.active_session`، وهو لا يحمل اسم
    الجلسة بل اسم **نافذة الـkill zone** الضيقة: لندن 07–09 و11–13،
    نيويورك 13:30–15:30، آسيا 00–04. وما عداها «Inter-Session» — أي
    **12 ساعة من 24 بلا أي جلسة**، والفجوات 04–07 و09–11 و16–23.

    والشرط اسمه «London Session» لا «London Kill Zone»، وللـkill zones
    شرط منفصل بالمكتبة (`killzones`). فالتسمية كانت تَعِد بالجلسة
    وتُنفّذ نافذة ضيقة — وهو وعد مكسور لا إعداد متحفّظ: المستخدم يستبعد
    ساعات يظنها مشمولة.

    يُقرأ الوقت من لقطة التحليل متى توفّر، لا من `now`، حتى يوافق الحكم
    اللحظة التي قُيّم فيها التحليل فعلاً.
    """
    windows = _SESSION_WINDOWS.get(needle.upper())
    if not windows:
        return None

    kz = a.get("kill_zone") or {}
    hour = None
    raw = kz.get("current_time_utc")          # بصيغة "HH:MM UTC"
    if raw:
        try:
            hh, mm = str(raw).split(" ")[0].split(":")
            hour = int(hh) + int(mm) / 60.0
        except (ValueError, IndexError):
            hour = None
    if hour is None:
        if not kz:
            return None                        # لا بيانات ⇒ لا حكم
        from datetime import datetime, timezone as _tz
        now = datetime.now(_tz.utc)
        hour = now.hour + now.minute / 60.0

    return any(start <= hour < end for start, end in windows)


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
    "direction": _ext_direction,
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


def evaluate_condition(condition, analyses: Dict[str, Dict]) -> Optional[bool]:
    """Returns True/False if the condition type is supported and evaluable
    against the real analyze_market() result for THIS condition's own
    declared timeframe, or None if the type has no real implementation yet
    (or that timeframe's analysis couldn't be fetched this cycle)."""
    extractor = SUPPORTED_CONDITION_TYPES.get(condition.type)
    if not extractor:
        return None
    analysis = analyses.get(norm_timeframe(condition.timeframe))
    if analysis is None:
        return None
    result = extractor(analysis, condition.value)
    if result is None:
        return None
    return (not result) if condition.negate else result


def evaluate_strategy(groups: List, conditions: List, analyses: Dict[str, Dict], min_score: int, price: Optional[float] = None) -> Dict:
    """Pure evaluation of a strategy's saved groups/conditions. `analyses` is
    {timeframe: analyze_market() result} — one real, independent result per
    distinct timeframe actually used by the strategy's conditions (see
    distinct_timeframes()), each condition routed to its own. Unsupported
    conditions never count as a match — they're surfaced separately in
    `unsupported` for UI honesty."""
    enabled = [c for c in conditions if c.enabled]

    hit_by_id: Dict[int, bool] = {}
    unsupported_ids = set()
    unsupported = []
    for c in enabled:
        raw = evaluate_condition(c, analyses)
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
    groups_detail = []
    for g in groups_with_members:
        members = [c for c in enabled if c.group_id == g.id and c.id not in unsupported_ids]
        hits = sum(1 for c in members if hit_by_id.get(c.id))
        logic = g.logic.value
        if logic == "AND":
            ok = hits == len(members)
            need = len(members)
        elif logic == "OR":
            ok = hits > 0
            need = 1
        else:  # AT_LEAST
            need = g.at_least or 1
            ok = hits >= need
        groups_detail.append({
            "id": g.id, "name": getattr(g, "name", None) or f"#{g.id}",
            "logic": logic, "hits": hits, "members": len(members),
            "need": need, "passed": ok,
            "missing": [c.label for c in members if not hit_by_id.get(c.id)],
        })
        if not ok:
            groups_passed = False

    matched = [{"id": c.id, "label": c.label, "hit": hit_by_id.get(c.id, False)} for c in enabled]
    score_ok = score >= min_score
    triggered = bool(groups_passed and score_ok and len(enabled) > 0)

    # (2026-09-17) سبب عدم الإطلاق يُحسب ويُخزَّن، لا يُترك للمستخدم ليخمّنه.
    # بلاغ حقيقي: عتبة مضبوطة على 50 وسجلّ يعرض "Score 54" مراراً بلا إطلاق،
    # فبدا الأمر عطلاً. والسبب أن الإطلاق يشترط أمرين لا واحداً — منطق
    # المجموعات **و** العتبة — وكان السجل يعرض الثاني فقط. فحين يتحقق
    # المعروض ولا يقع الإطلاق، يبدو النظام معطلاً وهو يعمل بالضبط كما
    # عُرّف. عرض الرقم دون شرطه إخفاءٌ بصيغة إظهار.
    block_reason = None
    if not enabled:
        block_reason = "لا شروط مفعّلة بهذه الاستراتيجية"
    elif not groups_passed:
        failed = [g for g in groups_detail if not g["passed"]]
        parts = []
        for g in failed:
            lg = {"AND": "الكل", "OR": "واحد على الأقل"}.get(g["logic"],
                                                            f"{g['need']} على الأقل")
            miss = ("، ينقص: " + "، ".join(g["missing"][:3])) if g["missing"] else ""
            parts.append(f"{g['name']} ({lg}) — تحقّق {g['hits']} من {g['members']}{miss}")
        detail = " · ".join(parts)
        if score_ok:
            block_reason = (f"الدرجة كافية ({score} ≥ {min_score}) "
                            f"لكن منطق المجموعات لم يكتمل: {detail}")
        else:
            block_reason = (f"الدرجة {score} دون العتبة {min_score}، "
                            f"ومنطق المجموعات لم يكتمل: {detail}")
    elif not score_ok:
        block_reason = f"منطق المجموعات مكتمل لكن الدرجة {score} دون العتبة {min_score}"

    return {
        "score": score,
        "score_ok": score_ok,
        "min_score": min_score,
        "groups_passed": groups_passed,
        "groups_detail": groups_detail,
        "block_reason": block_reason,
        "matched": matched,
        "unsupported": unsupported,
        "triggered": triggered,
        "price": price,
    }


def build_telegram_message(strategy, eval_result: Dict, symbol: str, timeframe: str, analysis: Dict) -> str:
    """Mirrors the frontend's tgTemplate builder, using real evaluation data."""
    levels = analysis.get("levels") or {}
    rec = analysis.get("recommendation") or "WAIT"

    # (2026-09-17) الاتجاه كان يُؤخذ من توصية المحرك وحدها، فتصل رسائل
    # مكتوب عليها "⚪ WAIT" ومعها دخول ووقف وهدف تصف صفقة شراء أو بيع
    # صريحة. بلاغ حقيقي: نُفّذت اثنتان منها على حساب تجريبي وبلغتا الهدف
    # بينما الرسالة تقول "انتظار" — فالمستخدم نفّذ صواباً رغم الرسالة لا
    # بسببها. والتناقض ليس تجميلياً: رسالة تحمل مستويات اتجاهية ولا تسمّي
    # اتجاهها تدفع لتخمينه، وتخمينه خطأً يعكس الصفقة.
    #
    # القاعدة: متى وُجدت مستويات فالاتجاه يُقرأ منها — الوقف تحت الدخول
    # شراء وفوقه بيع، بلا لبس. وتوصية المحرك تُذكر بجانبها متى خالفتها،
    # لأن الاستراتيجية أطلقت بشروط المستخدم لا بشروط المحرك، وإخفاء
    # الاختلاف يوهم باتفاق لا وجود له.
    entry_v = levels.get("entry")
    sl_v    = levels.get("stop_loss")
    dir_from_levels = None
    if entry_v is not None and sl_v is not None:
        try:
            dir_from_levels = "BUY" if float(sl_v) < float(entry_v) else "SELL"
        except (TypeError, ValueError):
            dir_from_levels = None

    shown = dir_from_levels or rec
    direction_line = "🟢 LONG" if shown == "BUY" else ("🔴 SHORT" if shown == "SELL" else "⚪ WAIT")

    lines = ["━━━━━━━━━━━━━━", "🔥 STRATEGY TRIGGERED", "", f"{strategy.name}", f"{symbol}", f"{timeframe}", "",
              "Direction:", direction_line]
    if dir_from_levels and rec != dir_from_levels:
        lines += [f"(الاتجاه من مستويات الصفقة — محرّك التحليل يرى: {rec})"]

    if strategy.tg_send_entry and entry_v is not None:
        lines += ["", "Entry:", f"{entry_v}"]
    if strategy.tg_send_sl and sl_v is not None:
        lines += ["", "Stop Loss:", f"{sl_v}"]
    if strategy.tg_send_tp and levels.get("tp1") is not None:
        lines += ["", "Take Profit:", f"{levels.get('tp1')}"]
    if strategy.tg_send_rr and levels.get("risk_reward") is not None:
        lines += ["", "RR:", f"1:{levels.get('risk_reward')}"]

    # (2026-09-17) غياب المستويات كان صامتاً تماماً، فتصل رسالتان
    # متطابقتان لنفس الاستراتيجية والرمز إحداهما بمستويات والأخرى بلا —
    # بلا ما يفسّر الفرق. والسبب أن المحرك يمسحها عمداً حين ينحرف سعر
    # التحليل عن السوق فوق الحد المسموح (راجع rejection_reason
    # بـai_engine_v5)، وهو رفضُ سلامةٍ يجب أن يُقال لا أن يُحذف بصمت:
    # الصمت يجعل المستخدم يظن أن الإعداد معطّل، أو يستنتج مستويات من عنده.
    if strategy.tg_send_entry and entry_v is None:
        lines += ["", "⚠️ المستويات غير متاحة لهذا التقييم",
                  "(سعر التحليل انحرف عن السوق فوق الحد المسموح — "
                  "لم تُعرض مستويات قد تكون قديمة)"]

    if strategy.tg_send_confidence:
        # درجة الاستراتيجية لا ثقة المحرك — كانت تُسمّى Confidence فتُقرأ
        # على أنها تقييم المحرك للإشارة، وهما رقمان مختلفان تماماً.
        lines += ["", f"Score (شروطك): {eval_result['score']}%"]
    if strategy.tg_send_conditions:
        lines += ["", "Signals:"]
        for m in eval_result["matched"][:6]:
            if m["hit"]:
                lines.append(f"✓ {m['label']}")
    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)
