"""
Mosh AI Pro v5 - Gemini AI Engine (Professional Edition)
=========================================================
خبير تداول محترف بخبرة 10+ سنوات في ICT/SMC/Wyckoff
يتلقى البيانات الحقيقية ويعطي تحليلاً دقيقاً
"""

import json
import aiohttp
import pandas as pd
from loguru import logger
from app.config import get_settings

settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

EXPERT_SYSTEM_PROMPT = """
أنت خبير تداول محترف بخبرة 15 سنة في الأسواق المالية، متخصص في:

═══════════════════════════════════════════════
🏛️ ICT (Inner Circle Trader) - المستوى المتقدم
═══════════════════════════════════════════════
• Order Blocks: آخر شمعة هابطة/صاعدة قبل impulse قوي - أقوى مستوى دعم/مقاومة
• Fair Value Gaps (FVG): الفجوات السعرية التي يعود السعر لملئها بنسبة 70%+
• Liquidity Sweeps: اكتساح Equal Highs/Lows (SSL/BSL) قبل الانعكاس
• Market Structure: BOS (كسر هيكلي) + CHoCH (تغيير الطابع = مبكر جداً)
• Kill Zones: London Open (07-09 UTC) و NY Open (13:30-15:30 UTC) = أفضل التوقيتات
• Power of 3: Accumulation → Manipulation (False Break) → Distribution
• OTE: Optimal Trade Entry عند 61.8% Fibonacci من الحركة الأخيرة

═══════════════════════════════════════════════
📊 Wyckoff Method - فهم دورة السوق الكبرى
═══════════════════════════════════════════════
• Accumulation: المؤسسات تشتري بهدوء (حجم يرتفع مع السعر الثابت)
• Markup: الارتفاع المتسارع (دخول الجمهور)
• Distribution: المؤسسات تبيع (حجم عالٍ بدون تقدم سعري)
• Markdown: الانهيار

═══════════════════════════════════════════════
⚡ قواعد الدخول الصارمة (لا تخالفها أبداً)
═══════════════════════════════════════════════
1. لا تدخل إلا في Kill Zone أو بالقرب منها
2. لا تدخل إلا عند Order Block حقيقي أو FVG
3. يجب وجود BOS في اتجاه الصفقة
4. Premium = بيع / Discount = شراء
5. نسبة المخاطرة للعائد: لا تقل عن 1:2 (تفضيل 1:3)
6. وقف الخسارة دائماً خلف Swing Point + ATR
7. لا تعاكس الترند على TF أعلى

═══════════════════════════════════════════════
📐 تقييم جودة الإشارة
═══════════════════════════════════════════════
A+ (85-100): 5+ عوامل متقاطعة + Kill Zone + OB + FVG + BOS
A  (70-84):  4 عوامل + Kill Zone
B  (55-69):  3 عوامل كحد أدنى
C  (40-54):  2 عوامل - انتظر تأكيداً أكثر
WAIT (<40):  لا تدخل - المشهد غير واضح

الإجابة دائماً بـ JSON محدد فقط، بدون أي نص إضافي.
"""


def _build_professional_prompt(symbol: str, timeframe: str, ict_data: dict, df_tail: list) -> str:
    """بناء Prompt احترافي مع بيانات حقيقية"""

    # مستخرج المعلومات المهمة فقط
    confluence = ict_data.get("confluence", {})
    structure = ict_data.get("market_structure", {})
    ob = ict_data.get("order_blocks", {})
    fvg_data = ict_data.get("fvg", {})
    liq = ict_data.get("liquidity", {})
    pd_zone = ict_data.get("premium_discount", {})
    kz = ict_data.get("kill_zone", {})
    wy = ict_data.get("wyckoff", {})
    ind = ict_data.get("indicators", {})

    summary = {
        "رمز": symbol,
        "إطار_زمني": timeframe,
        "السعر_الحالي": ict_data.get("current_price"),
        "ATR": ict_data.get("atr"),

        "هيكل_السوق": {
            "الترند": structure.get("trend"),
            "النمط": structure.get("structure"),
            "آخر_BOS": structure.get("last_bos"),
            "CHoCH": structure.get("choch_events", []),
        },

        "Order_Blocks": {
            "صاعد": ob.get("bullish_obs", [])[:2],
            "هابط": ob.get("bearish_obs", [])[:2],
            "في_OB_صاعد": ob.get("in_bullish_ob"),
            "في_OB_هابط": ob.get("in_bearish_ob"),
        },

        "FVG": {
            "صاعد": fvg_data.get("bullish_fvgs", [])[:2],
            "هابط": fvg_data.get("bearish_fvgs", [])[:2],
            "في_FVG_صاعد": fvg_data.get("in_bullish_fvg"),
            "في_FVG_هابط": fvg_data.get("in_bearish_fvg"),
        },

        "السيولة": {
            "BSL_Equal_Highs": liq.get("equal_highs", [])[:2],
            "SSL_Equal_Lows": liq.get("equal_lows", [])[:2],
            "الانحياز": liq.get("bias"),
        },

        "منطقة_Premium_Discount": {
            "المنطقة": pd_zone.get("zone"),
            "النسبة_المئوية": pd_zone.get("pct"),
            "Equilibrium": pd_zone.get("equilibrium"),
            "OTE_61.8": pd_zone.get("ote_level"),
        },

        "Kill_Zone": {
            "الجلسة": kz.get("active_session"),
            "وقت_مثالي": kz.get("is_optimal_time"),
            "الوقت_الحالي": kz.get("current_time_utc"),
        },

        "Wyckoff": {
            "المرحلة": wy.get("phase"),
            "الإجراء": wy.get("action"),
        },

        "المؤشرات": {
            "RSI": ind.get("rsi"),
            "MACD": ind.get("macd"),
            "EMA_20": ind.get("ema_20"),
            "EMA_50": ind.get("ema_50"),
            "Stoch_K": ind.get("stoch_k"),
        },

        "التقاطع_التقني": {
            "الاتجاه": confluence.get("direction"),
            "الثقة": confluence.get("confidence"),
            "عوامل_الصعود": confluence.get("factors", [])[:5] if confluence.get("direction") == "BUY" else [],
            "عوامل_الهبوط": confluence.get("factors", [])[:5] if confluence.get("direction") == "SELL" else [],
            "عدد_العوامل": confluence.get("factor_count"),
        },

        "آخر_20_شمعة": df_tail,
    }

    return f"""
البيانات التقنية الكاملة لـ {symbol} على {timeframe}:

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

بناءً على خبرتك المهنية في ICT/SMC/Wyckoff وهذه البيانات:

أجب بـ JSON التالي فقط (لا نص إضافي):
{{
  "recommendation": "BUY|SELL|WAIT",
  "confidence_score": <0-100>,
  "signal_grade": "A+|A|B|C|WAIT",
  "entry_price": <رقم>,
  "stop_loss": <رقم>,
  "take_profit_1": <رقم>,
  "take_profit_2": <رقم>,
  "take_profit_3": <رقم أو null>,
  "risk_reward": <رقم>,
  "primary_reason": "<جملة واحدة: السبب الرئيسي للإشارة>",
  "ict_setup": "<اسم الـ Setup مثل: OB_Retest_FVG أو Liquidity_Sweep_BOS>",
  "analysis": {{
    "structure": "<تحليل هيكل السوق>",
    "smart_money": "<ماذا تفعل Smart Money الآن؟>",
    "entry_reasoning": "<لماذا هذا هو المستوى الصحيح للدخول>",
    "invalidation": "<متى تُلغى الإشارة؟>",
    "session_context": "<توقيت الدخول ومناسبته>"
  }},
  "confirmations": ["<عامل 1>", "<عامل 2>", "<عامل 3>"],
  "warnings": ["<تحذير إن وجد>"],
  "arabic_summary": "<ملخص احترافي في 2-3 جمل للمتداول العربي>"
}}
"""


class GeminiEngine:
    """محرك Gemini المحترف للتحليل الذكي"""

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key not in ["", "your_gemini_api_key_here"])
        if self.enabled:
            logger.success("✅ Gemini AI Engine مفعّل (Professional Mode)")
        else:
            logger.warning("⚠️ Gemini AI Engine غير مفعّل")

    async def analyze(self, symbol: str, timeframe: str, ict_data: dict, df: pd.DataFrame = None) -> dict:
        """تحليل احترافي مع بيانات الشموع الحقيقية"""
        if not self.enabled:
            return {}

        # آخر 20 شمعة للـ Prompt
        df_tail = []
        if df is not None and len(df) > 0:
            tail = df.tail(20)[["open", "high", "low", "close"]].round(5)
            df_tail = tail.to_dict("records")

        prompt = _build_professional_prompt(symbol, timeframe, ict_data, df_tail)

        payload = {
            "system_instruction": {
                "parts": [{"text": EXPERT_SYSTEM_PROMPT}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.15,      # منخفض = أكثر دقة وثباتاً
                "maxOutputTokens": 1500,
                "responseMimeType": "application/json",
            }
        }

        url = f"{GEMINI_API_URL}?key={self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
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
                    grade = result.get("signal_grade", "?")
                    rec = result.get("recommendation", "?")
                    conf = result.get("confidence_score", 0)
                    logger.success(f"🤖 Gemini: {symbol} → {rec} | Grade: {grade} | Confidence: {conf}%")
                    return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Gemini JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Gemini request failed: {e}")
            return {}

    def merge_with_ict(self, ict_data: dict, gemini: dict) -> dict:
        """
        دمج Gemini مع ICT Analysis
        Gemini يأخذ 70% وزن (فهو يرى الصورة الكاملة)
        """
        if not gemini:
            return ict_data

        gemini_conf = float(gemini.get("confidence_score", 0))
        ict_conf = float(ict_data.get("ai_confidence_score", 0))

        # متوسط مرجّح
        final_conf = round(gemini_conf * 0.70 + ict_conf * 0.30, 1)

        merged = {**ict_data}
        merged["ai_confidence_score"] = final_conf

        # توصية Gemini تُقدَّم إذا كان واثقاً
        if gemini_conf >= 50:
            merged["recommendation"] = gemini.get("recommendation", ict_data.get("recommendation"))

        # مستويات Gemini (أدق من ICT لأنه يرى السياق)
        if gemini.get("entry_price"):
            merged["entry_zones"] = [gemini["entry_price"]]
        if gemini.get("stop_loss"):
            merged["stop_loss_zone"] = gemini["stop_loss"]

        tps = [v for v in [
            gemini.get("take_profit_1"),
            gemini.get("take_profit_2"),
            gemini.get("take_profit_3")
        ] if v]
        if tps:
            merged["take_profit_zones"] = tps

        if gemini.get("risk_reward"):
            merged["risk_reward_ratio"] = gemini["risk_reward"]

        # تحليل Gemini المفصّل
        merged["gemini_analysis"] = {
            "enabled": True,
            "confidence": gemini_conf,
            "signal_grade": gemini.get("signal_grade", "?"),
            "ict_setup": gemini.get("ict_setup", ""),
            "primary_reason": gemini.get("primary_reason", ""),
            "arabic_summary": gemini.get("arabic_summary", ""),
            "confirmations": gemini.get("confirmations", []),
            "warnings": gemini.get("warnings", []),
            "detailed_analysis": gemini.get("analysis", {}),
        }

        return merged


# Singleton
gemini_engine = GeminiEngine()
