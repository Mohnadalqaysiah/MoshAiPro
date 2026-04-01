"""
Mosh AI Pro v5 - Gemini AI Engine (Professional Edition v2)
============================================================
Quantitative Market Analyst — ICT/SMC + Wyckoff + Multi-Timeframe
"""

import json
import aiohttp
import pandas as pd
from loguru import logger
from app.config import get_settings

settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

EXPERT_SYSTEM_PROMPT = """
أنت محلل أسواق مالية كمّي (Quantitative Market Analyst) بخبرة 15+ سنة.
تخصصك: ICT/SMC + Wyckoff + Price Action المؤسسي.

═══════════════════════════════════════════════
⚠️ القواعد الحديدية (لا يمكن تجاوزها)
═══════════════════════════════════════════════

1. أنت لا تتوقع — أنت تقرأ ما تفعله المؤسسات من خلال البصمة السعرية
2. لا توصية بدون 3 عوامل تقاطع كحد أدنى
3. لا توصية عكس HTF Trend (4H/Daily)
4. لا توصية خلال 30 دقيقة قبل/بعد حدث اقتصادي عالي التأثير
5. لا توصية إذا كان ATR أقل من المعدل بـ 40%+ (سوق ميت)
6. لا توصية إذا كان Spread > 30% من ATR
7. Risk:Reward لا يقل عن 1:2 (مفضل 1:3+)
8. وقف الخسارة = Swing Point + (ATR × 0.5) كحد أدنى
9. لا تدخل أبداً في منتصف الحركة — انتظر Pullback
10. إذا شككت → الإجابة هي WAIT دائماً

═══════════════════════════════════════════════
🏛️ ICT Framework — قواعد التطبيق
═══════════════════════════════════════════════

### Order Blocks (OB)
- تعريف: آخر شمعة معاكسة قبل Impulse Move كبير
- شروط الصلاحية:
  • يجب أن يكون Impulse بعد OB ≥ 2× ATR
  • OB لم يُعاد اختباره أكثر من مرة (Fresh OB أقوى)
  • OB على HTF أقوى من LTF
  • Breaker Block (OB مكسور) = مقاومة/دعم جديد
- القوة: Strong (لم يُلمس) > Moderate (لُمس مرة) > Weak (لُمس مرتين+)

### Fair Value Gaps (FVG)
- تعريف: فجوة بين High شمعة 1 و Low شمعة 3
- الملء: 70%+ من FVGs تُملأ جزئياً على الأقل
- التصفية:
  • FVG ≥ 0.5× ATR = significant
  • FVG < 0.3× ATR = ضعيف (تجاهل)
  • FVG + OB في نفس المنطقة = Confluence Zone (أقوى إشارة)

### Liquidity Concepts
- BSL (Buy-Side Liquidity): Equal Highs / Swing Highs = مغناطيس للسعر
- SSL (Sell-Side Liquidity): Equal Lows / Swing Lows = مغناطيس للسعر
- Sweep ≠ Break:
  • Sweep = wick يتجاوز ثم يُغلق داخل → انعكاسي
  • Break = body يغلق فوق/تحت → استمراري
- Inducement: سيولة صغيرة داخل تصحيح → تُكتسح قبل الحركة الحقيقية

### Market Structure
- BOS (Break of Structure): كسر آخر HH/LL → تأكيد استمرار
- CHoCH (Change of Character): أول كسر معاكس → إنذار مبكر
- SMS (Shift in Market Structure): CHoCH + BOS في نفس الاتجاه الجديد → تأكيد انعكاس
- القاعدة: لا تتاجر CHoCH وحده — انتظر BOS للتأكيد

### Kill Zones (أوقات الذروة)
- Asian Range: 00:00-08:00 UTC → تحديد نطاق التلاعب
- London Open: 07:00-09:00 UTC → أعلى احتمالية لـ Manipulation
- London Close: 15:00-16:00 UTC → مصيدة سيولة متكررة
- NY Open: 13:00-15:30 UTC → أقوى حركة في اليوم
- NY PM: 19:00-21:00 UTC → عادةً تصحيح أو تهدئة
- ⚠️ خارج Kill Zones: لا تدخل إلا بتقاطع A+ واضح

### Power of 3 (AMD)
1. Accumulation: نطاق ضيق + حجم منخفض (غالباً Asian session)
2. Manipulation: كسر كاذب لأحد طرفي النطاق (London Open غالباً)
3. Distribution: الحركة الحقيقية في الاتجاه المعاكس (NY session غالباً)

### Premium/Discount + OTE
- Range = آخر Swing High - آخر Swing Low
- Equilibrium = 50% من Range
- Premium Zone = فوق 50% → منطقة بيع
- Discount Zone = تحت 50% → منطقة شراء
- OTE (Optimal Trade Entry) = 61.8%-78.6% Fibonacci retracement
- القاعدة: لا تشتري في Premium ولا تبيع في Discount

═══════════════════════════════════════════════
📊 Wyckoff — التطبيق المتقدم
═══════════════════════════════════════════════

### تحديد المرحلة
- Accumulation: نطاق ضيق + حجم يرتفع عند الدعم → Spring = شراء
- Markup: ارتفاع مستمر + حجم يرتفع مع السعر → Back-up = شراء
- Distribution: نطاق ضيق عالٍ + حجم يرتفع عند المقاومة → UTAD = بيع
- Markdown: انخفاض مستمر + حجم يرتفع مع الهبوط → LPSY = بيع

### Effort vs Result
- حجم عالٍ + حركة كبيرة = طبيعي (استمرار)
- حجم عالٍ + حركة صغيرة = امتصاص (انعكاس قريب)
- حجم منخفض + حركة كبيرة = فراغ سيولة (حركة ضعيفة)

═══════════════════════════════════════════════
📐 نظام التقييم المرجّح (Weighted Scoring)
═══════════════════════════════════════════════

| العامل                  | الوزن |
|------------------------|-------|
| HTF Trend Alignment    |  20   |
| BOS في اتجاه الصفقة    |  18   |
| Order Block (Fresh)    |  15   |
| Premium/Discount Zone  |  12   |
| FVG Confluence         |  10   |
| Kill Zone Timing       |   8   |
| Liquidity Sweep        |   7   |
| Wyckoff Confirmation   |   5   |
| RSI/Stoch Divergence   |   3   |
| EMA Alignment          |   2   |
| المجموع                | 100   |

### التصنيف:
- A+ (85-100): أقصى ثقة — دخول بـ 2% risk
- A  (70-84):  ثقة عالية — دخول بـ 1.5% risk
- B  (55-69):  مقبول — دخول بـ 1% risk
- C  (40-54):  ضعيف — 0.5% risk (أعطِ التوصية مع تحذير)
- WAIT (<40): لا تدخل — المشهد غير واضح

⚠️ قاعدة مهمة: لا تعطِ WAIT إلا إذا كانت الدرجة أقل من 40 فعلاً.
درجة 40-54 = توصية C مع تحذير، وليس WAIT.
درجة 55+ = توصية واضحة B أو أعلى.

═══════════════════════════════════════════════
💰 إدارة رأس المال (Position Sizing)
═══════════════════════════════════════════════

Position Size = (Account Balance × Risk%) / (Entry - SL)

Risk% حسب التصنيف: A+ = 2% | A = 1.5% | B = 1% | C = 0.5%

قواعد إضافية:
- Max 3 صفقات مفتوحة متزامنة
- Max 5% إجمالي المخاطرة المفتوحة
- بعد 3 خسائر متتالية: توقف 24 ساعة

═══════════════════════════════════════════════
🚪 استراتيجية الخروج الديناميكية
═══════════════════════════════════════════════

- TP1 (40% من الحجم): أقرب سيولة أو FVG معاكس
- TP2 (40% من الحجم): الهدف الرئيسي (Swing Point التالي)
- TP3 (20% من الحجم): امتداد 1.618 Fibonacci أو OB معاكس على HTF
- Trailing Stop: بعد TP1 → SL إلى Break Even | بعد TP2 → SL إلى TP1

═══════════════════════════════════════════════
🚨 قاعدة التحقق الإجباري — Trade Validation (لا استثناء أبداً)
═══════════════════════════════════════════════

قبل إرسال أي توصية BUY أو SELL، تحقق إجبارياً من:

في BUY:
  • entry_price < tp1 < tp2 < tp3  (الأهداف فوق الدخول)
  • stop_loss < entry_price         (الوقف أسفل الدخول)
  • R/R ≥ 1.2

في SELL:
  • tp3 < tp2 < tp1 < entry_price  (الأهداف أسفل الدخول)
  • stop_loss > entry_price         (الوقف فوق الدخول)
  • R/R ≥ 1.2

❌ إذا فشل أي شرط → غيّر التوصية فوراً إلى WAIT
❌ ممنوع إطلاقاً إرسال صفقة بمستويات معكوسة أو غير منطقية
❌ ممنوع SL فوق الدخول في BUY أو تحت الدخول في SELL

═══════════════════════════════════════════════
📊 وضع السوق (Market Mode) — الأساس في القرار
═══════════════════════════════════════════════

### TREND Mode (حقل market_mode.mode = "TREND"):
- الشرط: Wyckoff Markup/Markdown + BOS موجود
- القاعدة: يمكن الدخول بدون Sweep إذا توفر:
  ✔️ BOS في اتجاه الصفقة
  ✔️ Momentum قوي أو متوسط (momentum.strength ≠ WEAK)
  ✔️ Retest لمستوى BOS أو OB
  ✔️ HTF يؤكد نفس الاتجاه
- عند الدخول في TREND بدون Sweep: خفّض الثقة 15 نقطة

### RANGE Mode (حقل market_mode.mode = "RANGE"):
- الشرط: Wyckoff Accumulation/Distribution أو Sideways
- القاعدة: Sweep إجباري بالكامل
  ❌ لا Sweep = WAIT حتماً
  ❌ OBs متداخلة + لا BOS = WAIT حتماً

═══════════════════════════════════════════════
💧 قاعدة السيولة (ICT Liquidity Gate) — محدّثة
═══════════════════════════════════════════════

هذه القاعدة تعتمد على Market Mode:

### في RANGE Mode:
1. تحقق من "stop_hunt_analysis" في البيانات
2. إذا كان "has_bullish_sweep" = false وتفكر بـ BUY → WAIT
3. إذا كان "has_bearish_sweep" = false وتفكر بـ SELL → WAIT
4. Sweep + Rejection = دخول مسموح
5. Sweep بدون Rejection = WAIT

### في TREND Mode:
1. Sweep مفضّل لكن ليس إجبارياً
2. إذا توفر: BOS + momentum.strength = "STRONG" + HTF alignment → يمكن الدخول
3. إذا توفر: BOS + momentum.strength = "MODERATE" + 3 عوامل تقاطع → يمكن الدخول مع تخفيض 15 نقطة ثقة
4. إذا momentum.strength = "WEAK" → WAIT حتى في TREND

═══════════════════════════════════════════════
⚡ فلتر الزخم (Momentum Filter)
═══════════════════════════════════════════════

البيانات من حقل "momentum" في المدخلات:

- strength = "STRONG"   (score ≥ 70): يدعم الدخول في TREND
- strength = "MODERATE" (score ≥ 40): يدعم الدخول مع احتياط
- strength = "WEAK"     (score < 40):  يمنع الدخول إلا في A+ setup

### ما تبحث عنه:
- is_expanded = true + body_ratio > 0.7 = Institutional Displacement → قوي جداً
- consecutive_candles ≥ 3 = trend momentum → استمرار مؤكد
- expansion_ratio > 2.0 = spike مؤسسي → انتبه للاتجاه

═══════════════════════════════════════════════
🚫 منع Range Trap
═══════════════════════════════════════════════

حقل "range_conflict" في البيانات:
- إذا range_conflict.avoid_entry = true → WAIT إجباري
- لا تدخل عند تداخل OBs بدون BOS واضح
- هذا يمنع الدخول في وسط Range متضارب

═══════════════════════════════════════════════
📤 قاعدة المخرجات — WAIT vs Active Signal
═══════════════════════════════════════════════

### إذا recommendation = "WAIT":
❌ ممنوع إطلاقاً وضع: entry_price, stop_loss, tp1, tp2, tp3
✔️ ضع: watch_zones (مناطق المراقبة)
✔️ ضع: wait_reason (سبب الانتظار)
✔️ ضع: watch_level (أهم مستوى للمراقبة)

### إذا recommendation = "BUY" أو "SELL":
✔️ يجب أن تكون كل المستويات منطقية ومرتبة
BUY: stop_loss < entry_price < tp1 < tp2
SELL: tp2 < tp1 < entry_price < stop_loss

الإجابة دائماً بـ JSON محدد فقط، بدون أي نص إضافي.
"""


def _build_professional_prompt(
    symbol: str,
    timeframe: str,
    ltf_data: dict,       # 1H analysis (ICT)
    df_tail: list,        # آخر 20 شمعة 1H
    htf_data: dict = None,  # 4H analysis (ICT)
    account_balance: float = 10000.0,
    max_risk_percent: float = 1.5,
) -> str:
    """بناء Prompt احترافي v2 مع HTF+LTF والبيانات الحقيقية"""

    # ── HTF (4H) ──────────────────────────────────────────────────────────
    htf = htf_data or {}
    htf_structure = htf.get("market_structure", {})
    htf_ob = htf.get("order_blocks", {})
    htf_fvg = htf.get("fvg", {})
    htf_pd = htf.get("premium_discount", {})

    htf_bullish_obs = htf_ob.get("bullish_obs", [])[:1]
    htf_key_ob = htf_bullish_obs[0] if htf_bullish_obs else {}

    # ── LTF (1H) ──────────────────────────────────────────────────────────
    confluence = ltf_data.get("confluence", {})
    structure  = ltf_data.get("market_structure", {})
    ob         = ltf_data.get("order_blocks", {})
    fvg_data   = ltf_data.get("fvg", {})
    liq        = ltf_data.get("liquidity", {})
    pd_zone    = ltf_data.get("premium_discount", {})
    kz         = ltf_data.get("kill_zone", {})
    wy         = ltf_data.get("wyckoff", {})
    ind        = ltf_data.get("indicators", {})

    current_price = ltf_data.get("current_price", 0)
    atr           = ltf_data.get("atr", 0)
    atr_avg       = round(float(atr) * 1.15, 2) if atr else 0  # تقدير متوسط ATR

    # ── Liquidity Sweep Analysis (من ICT Engine الجديد) ──────────────────
    equal_lows  = liq.get("equal_lows", [])
    equal_highs = liq.get("equal_highs", [])
    sweep_data  = liq.get("sweep_analysis") or ltf_data.get("liquidity_sweep", {})

    # بناء recent_sweep من البيانات الحقيقية
    recent_sweep = {}
    if sweep_data.get("has_bullish_sweep"):
        ssl_info = sweep_data.get("ssl_sweep", {})
        recent_sweep = {
            "type":              "SSL_STOP_HUNT",
            "level":             ssl_info.get("level"),
            "wick_atr_ratio":    ssl_info.get("wick_atr_ratio"),
            "candles_since":     ssl_info.get("candles_since"),
            "rejection_confirmed": True,
            "quality":           sweep_data.get("sweep_quality"),
        }
    elif sweep_data.get("has_bearish_sweep"):
        bsl_info = sweep_data.get("bsl_sweep", {})
        recent_sweep = {
            "type":              "BSL_STOP_HUNT",
            "level":             bsl_info.get("level"),
            "wick_atr_ratio":    bsl_info.get("wick_atr_ratio"),
            "candles_since":     bsl_info.get("candles_since"),
            "rejection_confirmed": True,
            "quality":           sweep_data.get("sweep_quality"),
        }
    elif sweep_data.get("ssl_sweep"):
        ssl_info = sweep_data.get("ssl_sweep", {})
        recent_sweep = {
            "type":              "SSL_WEAK",
            "level":             ssl_info.get("level"),
            "rejection_confirmed": False,
            "candles_since":     ssl_info.get("candles_since"),
        }
    elif sweep_data.get("bsl_sweep"):
        bsl_info = sweep_data.get("bsl_sweep", {})
        recent_sweep = {
            "type":              "BSL_WEAK",
            "level":             bsl_info.get("level"),
            "rejection_confirmed": False,
            "candles_since":     bsl_info.get("candles_since"),
        }
    else:
        recent_sweep = {"type": "NONE", "rejection_confirmed": False}

    # ── News filter placeholder ────────────────────────────────────────────
    news_filter = ltf_data.get("news_filter", {
        "high_impact_next_4h": False,
        "event_name": None,
        "market_sentiment": "neutral"
    })

    # ── Determine asset class ─────────────────────────────────────────────
    crypto_symbols = {"BTCUSD", "ETHUSD", "BNBUSD"}
    asset_class = "crypto" if symbol.upper() in crypto_symbols else (
        "metals" if "XAU" in symbol.upper() or "XAG" in symbol.upper() else "forex"
    )

    input_schema = {
        "meta": {
            "symbol": symbol,
            "asset_class": asset_class,
            "timeframe_ltf": timeframe,
            "timeframe_htf": "4h",
            "account_balance": account_balance,
            "max_risk_percent": max_risk_percent,
        },

        "multi_timeframe": {
            "HTF_4h": {
                "trend": htf_structure.get("trend", "UNKNOWN"),
                "structure": htf_structure.get("structure", "UNKNOWN"),
                "last_BOS_price": htf_structure.get("last_bos"),
                "premium_discount": htf_pd.get("zone", "UNKNOWN"),
                "key_OB": htf_key_ob,
                "key_FVG": htf_fvg.get("bullish_fvgs", [{}])[:1][0] if htf_fvg.get("bullish_fvgs") else {},
            },
            "LTF_1h": {
                "trend": structure.get("trend", "UNKNOWN"),
                "structure": structure.get("structure", "UNKNOWN"),
                "last_BOS_price": structure.get("last_bos"),
                "CHoCH_detected": bool(structure.get("choch_events")),
                "CHoCH_price": structure.get("choch_events", [None])[0] if structure.get("choch_events") else None,
            },
        },

        "current_price": current_price,
        "ATR_14": round(float(atr), 5) if atr else 0,
        "ATR_14_avg_20": atr_avg,

        "order_blocks": {
            "bullish": ob.get("bullish_obs", [])[:2],
            "bearish": ob.get("bearish_obs", [])[:2],
            "price_in_bullish_OB": ob.get("in_bullish_ob", False),
            "price_in_bearish_OB": ob.get("in_bearish_ob", False),
        },

        "fair_value_gaps": {
            "bullish": fvg_data.get("bullish_fvgs", [])[:2],
            "bearish": fvg_data.get("bearish_fvgs", [])[:2],
            "price_in_bullish_FVG": fvg_data.get("in_bullish_fvg", False),
            "price_in_bearish_FVG": fvg_data.get("in_bearish_fvg", False),
        },

        "liquidity": {
            "BSL_unswept":         equal_highs[:3],
            "SSL_unswept":         equal_lows[:3],
            "nearest_BSL":         liq.get("nearest_bsl"),
            "nearest_SSL":         liq.get("nearest_ssl"),
            "bias":                liq.get("bias", "NEUTRAL"),
            "stop_hunt_analysis":  recent_sweep,
            "has_bullish_sweep":   sweep_data.get("has_bullish_sweep", False),
            "has_bearish_sweep":   sweep_data.get("has_bearish_sweep", False),
            "sweep_quality":       sweep_data.get("sweep_quality", "NONE"),
            "ICT_rule":            "لا دخول بدون Stop Hunt مؤكد (Sweep + Rejection)",
        },

        "premium_discount": {
            "swing_high": pd_zone.get("swing_high"),
            "swing_low": pd_zone.get("swing_low"),
            "equilibrium": pd_zone.get("equilibrium"),
            "current_zone": pd_zone.get("zone", "UNKNOWN"),
            "zone_percent": pd_zone.get("pct"),
            "OTE_618": pd_zone.get("ote_level"),
        },

        "session": {
            "current_session": kz.get("active_session"),
            "in_kill_zone": kz.get("is_optimal_time", False),
            "time_utc": kz.get("current_time_utc"),
        },

        "wyckoff": {
            "phase": wy.get("phase"),
            "action": wy.get("action"),
            "volume_confirmation": wy.get("confidence", 0) > 50,
        },

        "indicators": {
            "RSI_14": ind.get("rsi"),
            "MACD_histogram": ind.get("macd"),
            "EMA_20": ind.get("ema_20"),
            "EMA_50": ind.get("ema_50"),
            "EMA_200": ind.get("ema_200"),
            "Stoch_K": ind.get("stoch_k"),
            "Stoch_D": ind.get("stoch_d"),
            "volume_ratio": ind.get("volume_ratio"),
        },

        "confluence_score": {
            "direction": confluence.get("direction"),
            "confidence": confluence.get("confidence"),
            "factor_count": confluence.get("factor_count"),
            "factors": confluence.get("factors", [])[:6],
        },

        "news_filter": news_filter,

        "market_mode":    ltf_data.get("market_mode", {"mode": "RANGE", "sweep_required": True}),
        "momentum":       ltf_data.get("momentum", {"strength": "WEAK", "score": 0}),
        "range_conflict": ltf_data.get("range_conflict", {"avoid_entry": False}),

        "candles_ltf_last_20": df_tail,
    }

    return f"""
البيانات التقنية الكاملة لـ {symbol} | HTF: 4H | LTF: {timeframe}:

```json
{json.dumps(input_schema, ensure_ascii=False, indent=2)}
```

بناءً على خبرتك في ICT/SMC/Wyckoff وهذه البيانات الحقيقية، أجب بـ JSON التالي فقط (لا نص إضافي):

{{
  "schema_version": "2.0",
  "symbol": "{symbol}",

  "signal": {{
    "recommendation": "BUY|SELL|WAIT",
    "confidence_score": <0-100>,
    "signal_grade": "A+|A|B|C|WAIT",
    "ict_setup": "<اسم الـ Setup مثل: OTE+OB+FVG أو Liquidity_Sweep_BOS>"
  }},

  "trade_plan": {{
    "entry_price": <رقم>,
    "stop_loss": <رقم>,
    "sl_distance": <entry - sl>,
    "sl_in_ATR": <sl_distance / ATR>,
    "targets": {{
      "tp1": {{"price": <رقم>, "rr": <رقم>, "size_percent": 40, "reason": "<سبب>"}},
      "tp2": {{"price": <رقم>, "rr": <رقم>, "size_percent": 40, "reason": "<سبب>"}},
      "tp3": {{"price": <رقم أو null>, "rr": <رقم أو null>, "size_percent": 20, "reason": "<سبب أو null>"}}
    }},
    "risk_reward_avg": <متوسط RR>,
    "trailing_stop": "بعد TP1 → SL إلى Break Even | بعد TP2 → SL إلى TP1"
  }},

  "position_sizing": {{
    "account_balance": <account_balance>,
    "risk_percent": <حسب التصنيف: A+=2, A=1.5, B=1, C=0.5>,
    "risk_amount": <balance * risk_percent / 100>,
    "position_size": <risk_amount / sl_distance>,
    "unit": "<BTC|lot|oz>"
  }},

  "scoring_breakdown": {{
    "htf_alignment":    {{"score": <0-20>, "max": 20, "note": "<ملاحظة>"}},
    "bos_direction":    {{"score": <0-18>, "max": 18, "note": "<ملاحظة>"}},
    "order_block":      {{"score": <0-15>, "max": 15, "note": "<ملاحظة>"}},
    "premium_discount": {{"score": <0-12>, "max": 12, "note": "<ملاحظة>"}},
    "fvg_confluence":   {{"score": <0-10>, "max": 10, "note": "<ملاحظة>"}},
    "kill_zone":        {{"score": <0-8>,  "max": 8,  "note": "<ملاحظة>"}},
    "liquidity_sweep":  {{"score": <0-7>,  "max": 7,  "note": "<ملاحظة>"}},
    "wyckoff":          {{"score": <0-5>,  "max": 5,  "note": "<ملاحظة>"}},
    "rsi_stoch":        {{"score": <0-3>,  "max": 3,  "note": "<ملاحظة>"}},
    "ema_alignment":    {{"score": <0-2>,  "max": 2,  "note": "<ملاحظة>"}},
    "total": <مجموع الدرجات>,
    "total_max": 100
  }},

  "analysis": {{
    "structure": "<تحليل HTF+LTF معاً>",
    "smart_money": "<ماذا تفعل المؤسسات الآن؟>",
    "entry_logic": "<لماذا هذا المستوى بالضبط؟>",
    "invalidation": "<متى تُلغى الإشارة؟>",
    "session_context": "<توقيت + Kill Zone>",
    "wyckoff_detail": "<المرحلة + Effort vs Result>",
    "risk_note": "<ملاحظة على ATR أو Spread>"
  }},

  "confirmations": ["<✅ عامل 1>", "<✅ عامل 2>", "..."],
  "warnings": ["<⚠️ تحذير إن وجد>"],

  "filters_passed": {{
    "htf_alignment": <true/false>,
    "no_high_impact_news": <true/false>,
    "atr_above_minimum": <true/false>,
    "spread_acceptable": true,
    "not_mid_move": <true/false>,
    "min_rr_met": <true/false>
  }},

  "arabic_summary": "<ملخص احترافي في 2-3 جمل: الإشارة + المستويات + حجم الصفقة>",

  "wait_info": {{
    "watch_zones": ["<منطقة مراقبة 1>", "<منطقة مراقبة 2>"],
    "wait_reason": "<سبب الانتظار الرئيسي>",
    "watch_level": <أهم سعر للمراقبة أو null>
  }}
}}
"""


class GeminiEngine:
    """محرك Gemini المحترف للتحليل الذكي v2"""

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key not in ["", "your_gemini_api_key_here"])
        if self.enabled:
            logger.success("✅ Gemini AI Engine v2 مفعّل (Quantitative Mode)")
        else:
            logger.warning("⚠️ Gemini AI Engine غير مفعّل")

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        ltf_data: dict,
        df: pd.DataFrame = None,
        htf_data: dict = None,
        account_balance: float = 10000.0,
        max_risk_percent: float = 1.5,
    ) -> dict:
        """تحليل احترافي v2 مع HTF+LTF وإدارة رأس المال"""
        if not self.enabled:
            return {}

        # آخر 20 شمعة LTF للـ Prompt
        df_tail = []
        if df is not None and len(df) > 0:
            tail = df.tail(20)[["open", "high", "low", "close"]].round(5)
            df_tail = tail.to_dict("records")

        prompt = _build_professional_prompt(
            symbol, timeframe, ltf_data, df_tail,
            htf_data=htf_data,
            account_balance=account_balance,
            max_risk_percent=max_risk_percent,
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": EXPERT_SYSTEM_PROMPT}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.10,       # أقل من v1 = أكثر دقة وثباتاً
                "maxOutputTokens": 2000,
                "responseMimeType": "application/json",
            }
        }

        url = f"{GEMINI_API_URL}?key={self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=40)
                ) as resp:

                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"❌ Gemini API {resp.status}: {body[:300]}")
                        return {}

                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

                    # تنظيف JSON
                    if text.startswith("```"):
                        lines = text.split("\n")
                        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                    if text.startswith("json"):
                        text = text[4:].strip()

                    result = json.loads(text)
                    sig = result.get("signal", {})
                    grade = sig.get("signal_grade", "?")
                    rec   = sig.get("recommendation", "?")
                    conf  = sig.get("confidence_score", 0)
                    total = result.get("scoring_breakdown", {}).get("total", 0)
                    logger.success(
                        f"🤖 Gemini v2: {symbol} → {rec} | Grade: {grade} | "
                        f"Score: {total}/100 | Confidence: {conf}%"
                    )
                    return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Gemini JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Gemini request failed: {e}")
            return {}

    def merge_with_ict(self, ict_data: dict, gemini: dict) -> dict:
        """
        دمج Gemini v2 مع ICT Analysis
        Gemini v2 يأخذ 75% وزن (يرى HTF+LTF + Position Sizing)
        """
        if not gemini:
            return ict_data

        sig        = gemini.get("signal", {})
        trade_plan = gemini.get("trade_plan", {})
        targets    = trade_plan.get("targets", {})
        scoring    = gemini.get("scoring_breakdown", {})
        pos_size   = gemini.get("position_sizing", {})
        analysis   = gemini.get("analysis", {})
        filters    = gemini.get("filters_passed", {})

        gemini_conf = float(sig.get("confidence_score", 0))
        ict_conf    = float(ict_data.get("ai_confidence_score", 0))
        final_conf  = round(gemini_conf * 0.75 + ict_conf * 0.25, 1)

        merged = {**ict_data}
        merged["ai_confidence_score"] = final_conf

        # توصية Gemini: اقبلها إذا الثقة >= 40 حتى لو بعض الفلاتر فاشلة
        # WAIT فقط إذا الثقة < 40 أو الفلاتر الحيوية فاشلة
        critical_filters_ok = filters.get("htf_alignment", True) and filters.get("min_rr_met", True)
        if gemini_conf >= 40 and critical_filters_ok:
            merged["recommendation"] = sig.get("recommendation", ict_data.get("recommendation"))
        elif gemini_conf < 40 or not critical_filters_ok:
            merged["recommendation"] = "WAIT"

        # مستويات الدخول والخروج من Gemini (أدق)
        g_entry = trade_plan.get("entry_price")
        g_sl    = trade_plan.get("stop_loss")
        g_tp1   = targets.get("tp1", {}).get("price")
        g_tp2   = targets.get("tp2", {}).get("price")
        g_tp3   = targets.get("tp3", {}).get("price")

        if g_entry:
            merged["entry_zones"] = [g_entry]
        if g_sl:
            merged["stop_loss_zone"] = g_sl

        tps = [t for t in [g_tp1, g_tp2, g_tp3] if t]
        if tps:
            merged["take_profit_zones"] = tps

        # ── مزامنة levels dict (يُقرأ من البوت والمنصة) ─────────────────
        if g_entry or g_sl or g_tp1:
            rec     = merged.get("recommendation", "")
            g_e     = g_entry or 0
            g_s     = g_sl    or 0
            g_t1    = g_tp1   or 0
            # تحقق اتجاه صحيح قبل المزامنة
            buy_ok  = rec == "BUY"  and g_s < g_e < g_t1
            sell_ok = rec == "SELL" and g_t1 < g_e < g_s
            if buy_ok or sell_ok:
                merged_levels = dict(ict_data.get("levels", {}))
                if g_entry: merged_levels["entry"] = g_entry
                if g_sl:    merged_levels["stop_loss"] = g_sl
                if g_tp1:   merged_levels["tp1"] = g_tp1
                if g_tp2:   merged_levels["tp2"] = g_tp2
                if g_tp3:   merged_levels["tp3"] = g_tp3
                # أعِد حساب zone حول entry الجديد
                atr_val = merged_levels.get("atr", 0)
                if atr_val and g_entry:
                    buf = atr_val * 0.25
                    if rec == "BUY":
                        merged_levels["entry_zone_min"] = round(g_entry - buf, 5)
                        merged_levels["entry_zone_max"] = round(g_entry + buf, 5)
                    else:
                        merged_levels["entry_zone_min"] = round(g_entry - buf, 5)
                        merged_levels["entry_zone_max"] = round(g_entry + buf, 5)
                merged["levels"] = merged_levels

        if trade_plan.get("risk_reward_avg"):
            merged["risk_reward_ratio"] = trade_plan["risk_reward_avg"]

        # Position Sizing
        merged["position_sizing"] = pos_size

        # Scoring Breakdown
        merged["scoring_breakdown"] = {
            "total": scoring.get("total", 0),
            "total_max": 100,
            "details": {
                k: v for k, v in scoring.items()
                if k not in ("total", "total_max")
            }
        }

        # تحليل Gemini الكامل
        merged["gemini_analysis"] = {
            "enabled": True,
            "version": "2.0",
            "confidence": gemini_conf,
            "signal_grade": sig.get("signal_grade", "?"),
            "ict_setup": sig.get("ict_setup", ""),
            "arabic_summary": gemini.get("arabic_summary", ""),
            "confirmations": gemini.get("confirmations", []),
            "warnings": gemini.get("warnings", []),
            "filters_passed": filters,
            "detailed_analysis": analysis,
            "trade_plan": trade_plan,
        }

        return merged


# Singleton
gemini_engine = GeminiEngine()
