"""
Mosh AI Pro v5 - Gemini AI Engine
تكامل Google Gemini لتحليل الأسواق بناءً على مدارس ICT / SMC / Wyckoff
"""

import json
import aiohttp
from loguru import logger
from app.config import get_settings

settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """
أنت خبير تداول متخصص في مدارس التداول الاحترافية:

📐 **Wyckoff Method**: تحليل دورات التراكم والتوزيع، تحديد مراحل Wyckoff (Accumulation, Markup, Distribution, Markdown)
💧 **ICT / Smart Money Concepts (SMC)**:
   - Order Blocks, Breaker Blocks
   - Fair Value Gaps (FVG)
   - Equal Highs/Lows (Liquidity Pools)
   - Market Structure Shifts (BOS / CHoCH)
   - Kill Zones (London, NY, Asia sessions)
   - Premium & Discount Zones (Fibonacci 50%)
💹 **Price Action**:
   - تحليل هيكل السوق (HH, HL, LH, LL)
   - مناطق الدعم والمقاومة
   - الشموع اليابانية
📊 **Volume Analysis**:
   - Volume Profile
   - Smart Money Volume

مهمتك:
1. تحليل البيانات التقنية المعطاة
2. تحديد الفرصة التداولية بدقة
3. تقديم توصية واضحة: BUY / SELL / WAIT
4. شرح السبب بناءً على المدارس أعلاه
5. تحديد مستويات الدخول، وقف الخسارة، الأهداف

قواعد مهمة:
- لا توصي بالدخول إلا إذا توافرت على الأقل 3 عوامل تأكيد
- كن محدداً في الأرقام
- استخدم مصطلحات المدارس المذكورة
- أجب دائماً بصيغة JSON
"""


def _build_analysis_prompt(symbol: str, timeframe: str, technical_data: dict) -> str:
    """بناء الـ Prompt للتحليل"""

    data_summary = {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": technical_data.get("current_price"),
        "atr": technical_data.get("atr"),

        "trend": technical_data.get("trend", {}),
        "market_structure": technical_data.get("market_structure", {}),

        "wyckoff": {
            "phase": technical_data.get("wyckoff_analysis", {}).get("phase"),
            "action": technical_data.get("wyckoff_analysis", {}).get("action"),
            "confidence": technical_data.get("wyckoff_analysis", {}).get("confidence"),
        },

        "premium_discount": {
            "zone": technical_data.get("premium_discount", {}).get("current_zone"),
            "bias": technical_data.get("premium_discount", {}).get("bias"),
            "confidence": technical_data.get("premium_discount", {}).get("confidence"),
        },

        "liquidity": {
            "equal_highs": technical_data.get("liquidity_analysis", {}).get("equal_highs", [])[:3],
            "equal_lows": technical_data.get("liquidity_analysis", {}).get("equal_lows", [])[:3],
            "bias": technical_data.get("liquidity_analysis", {}).get("bias", {}),
        },

        "volume": {
            "trend": technical_data.get("volume_analysis", {}).get("trend"),
            "smart_money": technical_data.get("volume_analysis", {}).get("smart_money_activity"),
        },

        "killzone": {
            "active": technical_data.get("killzones", {}).get("active_session"),
            "is_optimal": technical_data.get("killzones", {}).get("is_optimal_time"),
        },

        "bos": {
            "direction": technical_data.get("bos_analysis", {}).get("current_trend"),
            "last_bos": technical_data.get("bos_analysis", {}).get("last_bos"),
        },

        "breaker_blocks": technical_data.get("breaker_blocks", {}).get("blocks", [])[:2],

        "current_ai_score": technical_data.get("ai_confidence_score", 0),
    }

    return f"""
بيانات التحليل التقني لـ {symbol} على الإطار الزمني {timeframe}:

```json
{json.dumps(data_summary, ensure_ascii=False, indent=2)}
```

بناءً على هذه البيانات وخبرتك في مدارس ICT/SMC/Wyckoff:

1. حلّل الوضع الحالي للسوق
2. حدد ما إذا كانت هناك فرصة تداول
3. قدم التوصية

أجب بالضبط بهذا الـ JSON (لا تضف أي نص خارجه):
{{
  "recommendation": "BUY|SELL|WAIT",
  "confidence_score": <0-100>,
  "entry_price": <رقم أو null>,
  "stop_loss": <رقم أو null>,
  "take_profit_1": <رقم أو null>,
  "take_profit_2": <رقم أو null>,
  "risk_reward": <رقم أو null>,
  "primary_reason": "<السبب الرئيسي بجملة واحدة>",
  "analysis": {{
    "wyckoff_insight": "<تحليل Wyckoff>",
    "smc_insight": "<تحليل SMC/ICT>",
    "structure_insight": "<هيكل السوق>",
    "timing_insight": "<توقيت الدخول والـ Kill Zones>"
  }},
  "confirmations": ["<عامل 1>", "<عامل 2>", "<عامل 3>"],
  "warnings": ["<تحذير 1 إن وجد>"],
  "arabic_summary": "<ملخص شامل بالعربية في 3-4 جمل>"
}}
"""


class GeminiEngine:
    """محرك Gemini للتحليل الذكي"""

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key != "your_gemini_api_key_here")
        if self.enabled:
            logger.success("✅ Gemini AI Engine مفعّل")
        else:
            logger.warning("⚠️ Gemini AI Engine غير مفعّل (لا يوجد API Key)")

    async def analyze(self, symbol: str, timeframe: str, technical_data: dict) -> dict:
        """
        تحليل البيانات التقنية باستخدام Gemini

        Returns:
            dict بنتائج Gemini أو dict فارغ إذا فشل
        """
        if not self.enabled:
            return {}

        prompt = _build_analysis_prompt(symbol, timeframe, technical_data)

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
            }
        }

        url = f"{GEMINI_API_URL}?key={self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload,
                                        timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"❌ Gemini API error {resp.status}: {body[:200]}")
                        return {}

                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]

                    # نظف JSON إذا جاء مغلفاً
                    text = text.strip()
                    if text.startswith("```"):
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]

                    result = json.loads(text)
                    logger.success(f"✅ Gemini: {symbol} → {result.get('recommendation')} ({result.get('confidence_score')}%)")
                    return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Gemini JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Gemini request failed: {e}")
            return {}

    def merge_with_technical(self, technical: dict, gemini: dict) -> dict:
        """
        دمج نتائج Gemini مع التحليل التقني الأصلي
        Gemini يأخذ أولوية في التوصية إذا كانت الثقة أعلى
        """
        if not gemini:
            return technical

        gemini_conf = gemini.get("confidence_score", 0)
        tech_conf   = technical.get("ai_confidence_score", 0)

        # الثقة النهائية: متوسط مرجّح (Gemini أثقل لأنه أذكى)
        final_conf = round((gemini_conf * 0.65) + (tech_conf * 0.35), 1)

        merged = {**technical}

        # إذا Gemini واثق أكثر من 55% → خذ توصيته
        if gemini_conf >= 55:
            merged["recommendation"] = gemini.get("recommendation", technical.get("recommendation"))

        merged["ai_confidence_score"] = final_conf

        # أضف مستويات Gemini إذا توفرت
        if gemini.get("entry_price"):
            merged["entry_zones"] = [gemini["entry_price"]]
        if gemini.get("stop_loss"):
            merged["stop_loss_zone"] = gemini["stop_loss"]
        if gemini.get("take_profit_1") or gemini.get("take_profit_2"):
            tps = [v for v in [gemini.get("take_profit_1"), gemini.get("take_profit_2")] if v]
            merged["take_profit_zones"] = tps
        if gemini.get("risk_reward"):
            merged["risk_reward"] = gemini["risk_reward"]

        # أضف تحليل Gemini كحقل منفصل
        merged["gemini_analysis"] = {
            "enabled": True,
            "confidence": gemini_conf,
            "primary_reason": gemini.get("primary_reason", ""),
            "arabic_summary": gemini.get("arabic_summary", ""),
            "confirmations": gemini.get("confirmations", []),
            "warnings": gemini.get("warnings", []),
            "insights": gemini.get("analysis", {}),
        }

        return merged


# Singleton
gemini_engine = GeminiEngine()
