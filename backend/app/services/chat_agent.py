"""
Mosh AI Pro v5 - Trading Chat Agent
وكيل محادثة ذكي متخصص في التداول والتحليل
"""

import json
import aiohttp
from loguru import logger
from app.config import get_settings
from app.services.rate_limiter import twelvedata_client

settings = get_settings()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

AGENT_SYSTEM_PROMPT = """
أنت "مُوش" - مساعد تداول ذكي متخصص في تحليل الأسواق المالية، ومهمتك الأساسية
هي تفسير نتائج محرك التحليل في منصة Mosh AI Pro وتقديمها للمستخدم بشكل واضح
وعملي، بدون اختراع أرقام جديدة.

هويتك:
- خبير في مدارس ICT (Inner Circle Trader) و SMC (Smart Money Concepts)
- متخصص في Wyckoff Method وتحليل السيولة
- تتحدث العربية بطلاقة مع استخدام المصطلحات الإنجليزية التقنية
- دقيق، منظم، وعملي في توصياتك وتفسيراتك

قدراتك:
1. تحليل الأسواق (XAUUSD، BTCUSD، EURUSD، GBPUSD، USDJPY، USDCHF)
2. شرح مفاهيم التداول (Order Blocks، FVG، BOS، Wyckoff، إلخ)
3. إعطاء توصيات بناءً على التحليل القادم من المحرك الداخلي (لا تخترع قيماً)
4. تفسير البيانات التقنية (الاتجاه، السيولة، مناطق الدخول والأهداف، R/R، إلخ)
5. إنشاء تقارير تداول تفصيلية

قواعد مهمة:
- الأرقام (مناطق الدخول، الأهداف، وقف الخسارة، R/R، الثقة، الاتجاه ...) يجب أن
  تأتي حصراً من بيانات التحليل التي تصلك في السياق (لا تقم بتقديرها من عندك).
- لا تعطِ توصيات دخول إلا بعد وجود تحليل فعلي في البيانات.
- دائماً نبّه على المخاطر، وأن التحليل تعليمي وليس نصيحة استثمارية مباشرة.
- إذا طُلب تحليل زوج أو تقرير أو شموع → استخدم بيانات التحليل والشموع المتوفرة
  في السياق قدر الإمكان.

تنسيق الرد (مهم جداً):
- يجب دائماً أن تعيد JSON يحتوي على الحقول التالية:
  - "action": نوع الرد "text" | "analyze" | "chart" | "report"
  - "message": نص عربي مفصل يشرح التحليل/الفرصة/التقرير للمستخدم
  - يمكن إضافة حقول أخرى مساعدة، لكن لا تحذف "action" ولا "message".

أمثلة:
- إجابة تحليل (مع شرح واسع):
  {
    "action": "analyze",
    "symbol": "XAUUSD",
    "timeframe": "1h",
    "message": "ملخص التحليل لـ XAUUSD على فريم الساعة: ... (نص عربي مفصل يفسّر
    التوصية، الثقة، مناطق الدخول، وقف الخسارة، الأهداف، R/R، وسيولة السوق مع
    تنبيه على المخاطر)"
  }

- إجابة رسم شموع:
  {
    "action": "chart",
    "symbol": "BTCUSD",
    "timeframe": "1h",
    "message": "تم تجهيز رسم الشموع لـ BTCUSD على فريم الساعة. استخدم الرسم لقراءة
    البريك أوف ستراكشر، مناطق الطلب/العرض، وتأكيد التحليل."
  }

- إجابة تقرير:
  {
    "action": "report",
    "symbol": "EURUSD",
    "message": "تقرير تداول تفصيلي لـ EURUSD: ... (ملخص السيناريوهات المحتملة،
    مناطق التداول، السيناريو البديل، وإدارة المخاطر)"
  }

- إجابة نصية عامة:
  {
    "action": "text",
    "message": "Order Block هو منطقة ..."
  }
"""


class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role    = role     # "user" | "assistant"
        self.content = content


class TradingChatAgent:
    """وكيل محادثة التداول"""

    MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
    TIMEFRAMES = ["15min", "1h", "4h", "1day"]

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key not in ("", "your_gemini_api_key_here"))
        # تاريخ المحادثة لكل جلسة
        self.sessions: dict[str, list] = {}

    def _detect_intent(self, message: str) -> dict:
        """كشف نية المستخدم من رسالته"""
        msg_lower = message.lower()

        # كشف الأزواج
        symbol = None
        for m in self.MARKETS:
            if m.lower() in msg_lower or m[:3].lower() in msg_lower:
                symbol = m
                break
        # اسماء شائعة
        if not symbol:
            if any(w in msg_lower for w in ["ذهب", "gold", "xau"]):
                symbol = "XAUUSD"
            elif any(w in msg_lower for w in ["بيتكوين", "bitcoin", "btc"]):
                symbol = "BTCUSD"
            elif any(w in msg_lower for w in ["يورو", "euro", "eur"]):
                symbol = "EURUSD"
            elif any(w in msg_lower for w in ["جنيه", "pound", "gbp"]):
                symbol = "GBPUSD"

        # كشف الإطار الزمني
        timeframe = "1h"
        if any(w in msg_lower for w in ["15", "خمس عشر", "ربع ساعة"]):
            timeframe = "15min"
        elif any(w in msg_lower for w in ["4h", "4 ساعات", "أربع"]):
            timeframe = "4h"
        elif any(w in msg_lower for w in ["يومي", "daily", "1d"]):
            timeframe = "1day"

        # كشف النوع
        is_analysis = any(w in msg_lower for w in [
            "حلل", "تحليل", "analyze", "signal", "إشارة", "فرصة", "opportunity",
            "شراء", "بيع", "buy", "sell", "دخول", "entry"
        ])
        is_chart = any(w in msg_lower for w in [
            "شموع", "رسم", "chart", "رسم بياني", "شمعة", "candlestick"
        ])
        is_report = any(w in msg_lower for w in [
            "تقرير", "report", "ملخص", "summary"
        ])

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "is_analysis": is_analysis,
            "is_chart": is_chart,
            "is_report": is_report,
        }

    async def _fetch_analysis(self, symbol: str, timeframe: str) -> dict:
        """جلب التحليل من الـ API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:8000/api/v1/signals/analyze"
                params = {"symbol": symbol, "timeframe": timeframe, "advanced_mode": "true"}
                async with session.post(url, params=params, timeout=aiohttp.ClientTimeout(total=40)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {})
        except Exception as e:
            logger.error(f"Chat fetch analysis error: {e}")
        return {}

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 50) -> list:
        """جلب بيانات الشموع"""
        try:
            df = await twelvedata_client.get_ohlcv(symbol, timeframe, outputsize=limit)
            if df is None:
                return []
            candles = []
            for _, row in df.tail(limit).iterrows():
                candles.append({
                    "time":  row["datetime"].isoformat(),
                    "open":  float(row["open"]),
                    "high":  float(row["high"]),
                    "low":   float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0)),
                })
            return candles
        except Exception as e:
            logger.error(f"Chat fetch candles error: {e}")
            return []

    def _build_analysis_context(self, analysis: dict, symbol: str, timeframe: str) -> str:
        """بناء سياق التحليل لإرساله لـ Gemini"""
        rec  = analysis.get("recommendation", "WAIT")
        conf = analysis.get("ai_confidence_score", 0)
        trend = analysis.get("trend", {})
        pd_zone = analysis.get("premium_discount", {})
        wyckoff = analysis.get("wyckoff_analysis", {})
        liquidity = analysis.get("liquidity_analysis", {})
        entry = analysis.get("entry_zones", [])
        sl    = analysis.get("stop_loss_zone")
        tps   = analysis.get("take_profit_zones", [])
        rr    = analysis.get("risk_reward_ratio") or analysis.get("risk_reward")

        return f"""
نتائج التحليل التقني لـ {symbol} ({timeframe}):
- التوصية: {rec}
- نسبة الثقة: {conf:.1f}%
- الاتجاه: {trend.get('direction','N/A')} بقوة {trend.get('strength',0)}%
- منطقة Premium/Discount: {pd_zone.get('current_zone','N/A')}
- مرحلة Wyckoff: {wyckoff.get('phase','N/A')}
- السيولة: {liquidity.get('bias',{}).get('direction','N/A')}
- مناطق الدخول: {entry}
- وقف الخسارة: {sl}
- الأهداف: {tps}
- نسبة R/R: {rr}

تحليل Gemini: {json.dumps(analysis.get('gemini_analysis',{}), ensure_ascii=False)}
"""

    def _build_analysis_summary(self, analysis: dict, symbol: str, timeframe: str) -> str:
        """بناء نص عربي واضح من نتائج التحليل الداخلية بدون الاعتماد على Gemini"""
        rec = analysis.get("recommendation", "WAIT")
        rec_map = {"BUY": "شراء", "SELL": "بيع", "WATCH": "مراقبة", "WAIT": "انتظار"}
        rec_ar = rec_map.get(rec, rec)

        conf = analysis.get("ai_confidence_score", 0)
        trend = analysis.get("trend", {})
        pd_zone = analysis.get("premium_discount", {})
        wyckoff = analysis.get("wyckoff_analysis", {})
        liquidity = analysis.get("liquidity_analysis", {})
        entry = analysis.get("entry_zones", [])
        sl = analysis.get("stop_loss_zone")
        tps = analysis.get("take_profit_zones", [])
        rr = analysis.get("risk_reward_ratio") or analysis.get("risk_reward")

        lines = []
        lines.append(f"ملخص تحليل {symbol} على فريم {timeframe}:")
        lines.append(f"- التوصية الحالية: {rec_ar} ({rec}) بثقة تقريبية {conf:.1f}%.")

        if trend:
            direction = trend.get("direction", "غير محدد")
            strength = trend.get("strength", 0)
            lines.append(f"- اتجاه السوق: {direction} بقوة تقريبية {strength}%.")

        if pd_zone:
            cur_zone = pd_zone.get("current_zone", "غير معروف")
            lines.append(f"- موقع السعر بالنسبة لـ Premium/Discount: {cur_zone}.")

        if wyckoff:
            phase = wyckoff.get("phase")
            if phase:
                lines.append(f"- مرحلة Wyckoff الحالية المتوقعة: {phase}.")

        if liquidity:
            bias = liquidity.get("bias", {}).get("direction")
            if bias:
                lines.append(f"- انحياز السيولة: {bias}.")

        if entry:
            lines.append(f"- مناطق الدخول المقترحة: {entry}.")

        if sl:
            lines.append(f"- منطقة وقف الخسارة المقترحة: {sl}.")

        if tps:
            lines.append(f"- مناطق جني الأرباح المحتملة: {tps}.")

        if rr:
            lines.append(f"- نسبة العائد إلى المخاطرة التقريبية (R/R): {rr}.")

        lines.append("")
        lines.append(
            "⚠️ هذا التحليل آلي مبني على محرك المنصة، ويُستخدم لأغراض تعليمية "
            "وتحليلية فقط وليس نصيحة استثمارية مباشرة. احرص دائماً على إدارة "
            "مخاطرك والاعتماد على خطة تداولك الخاصة."
        )

        return "\n".join(lines)

    async def _call_gemini(self, messages: list, system_extra: str = "") -> str:
        """استدعاء Gemini API"""
        if not self.enabled:
            return json.dumps({
                "action": "text",
                "message": "⚠️ Gemini غير مفعّل. أضف GEMINI_API_KEY في الإعدادات."
            })

        history = []
        for msg in messages[-10:]:   # آخر 10 رسائل فقط
            history.append({
                "role":  "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })

        system = AGENT_SYSTEM_PROMPT
        if system_extra:
            system += f"\n\nمعلومات إضافية للرد:\n{system_extra}"

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": history,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{GEMINI_URL}?key={self.api_key}"
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Gemini chat error {resp.status}: {body[:200]}")
                        return json.dumps({"action": "text", "message": f"خطأ في Gemini: {resp.status}"})
                    data = await resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini chat request error: {e}")
            return json.dumps({"action": "text", "message": f"تعذر الاتصال بـ Gemini: {str(e)}"})

    async def chat(self, session_id: str, user_message: str) -> dict:
        """
        معالجة رسالة المستخدم وإرجاع الرد

        Returns:
            {
                "action": "text|analyze|chart|report",
                "message": "...",
                "data": {...}   # التحليل أو الشموع إذا طُلبت
            }
        """
        # تهيئة الجلسة
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        history = self.sessions[session_id]
        history.append({"role": "user", "content": user_message})

        # كشف النية
        intent = self._detect_intent(user_message)
        extra_context = ""
        prefetched_data = {}

        # إذا طُلب تحليل → اجلب البيانات أولاً
        if intent["is_analysis"] and intent["symbol"]:
            symbol    = intent["symbol"]
            timeframe = intent["timeframe"]
            logger.info(f"🔍 Chat: جلب تحليل {symbol} {timeframe}")
            analysis = await self._fetch_analysis(symbol, timeframe)
            if analysis:
                extra_context = self._build_analysis_context(analysis, symbol, timeframe)
                prefetched_data["analysis"] = analysis
                prefetched_data["symbol"]   = symbol
                prefetched_data["timeframe"] = timeframe

        # إذا طُلب تقرير بدون أن يكون تحليل مُحضّر → اجلب التحليل أيضاً لدعم التقرير
        if intent["is_report"] and intent["symbol"] and "analysis" not in prefetched_data:
            symbol    = intent["symbol"]
            timeframe = intent["timeframe"]
            logger.info(f"📝 Chat: جلب تحليل للتقرير {symbol} {timeframe}")
            analysis = await self._fetch_analysis(symbol, timeframe)
            if analysis:
                extra_context += "\n\nبيانات تحليل للتقرير:\n" + self._build_analysis_context(analysis, symbol, timeframe)
                prefetched_data["analysis"] = analysis
                prefetched_data["symbol"]   = symbol
                prefetched_data["timeframe"] = timeframe

        # إذا طُلبت شموع → اجلبها
        if intent["is_chart"] and intent["symbol"]:
            symbol    = intent["symbol"]
            timeframe = intent["timeframe"]
            candles = await self._fetch_candles(symbol, timeframe, limit=60)
            if candles:
                prefetched_data["candles"]   = candles
                prefetched_data["symbol"]    = symbol
                prefetched_data["timeframe"] = timeframe
                extra_context += f"\n\nبيانات الشموع متاحة للرسم ({len(candles)} شمعة)"

        # اطلب من Gemini
        raw_response = await self._call_gemini(history, extra_context)

        # حاول تحليل JSON من الرد
        try:
            # Gemini قد يضيف markdown
            clean = raw_response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            response_obj = json.loads(clean)
        except Exception:
            # رد نصي عادي
            response_obj = {"action": "text", "message": raw_response}

        # أضف بيانات مسبقة الجلب
        action = response_obj.get("action", "text")

        if action == "analyze" and "analysis" in prefetched_data:
            response_obj["data"] = prefetched_data["analysis"]
            response_obj["symbol"] = prefetched_data.get("symbol")
            response_obj["timeframe"] = prefetched_data.get("timeframe")

        elif action == "chart" and "candles" in prefetched_data:
            response_obj["data"] = {"candles": prefetched_data["candles"]}
            response_obj["symbol"] = prefetched_data.get("symbol")
            response_obj["timeframe"] = prefetched_data.get("timeframe")

        elif "candles" in prefetched_data and action == "text":
            # إضافة الشموع مع الرد النصي
            response_obj["candles"] = prefetched_data["candles"]
            response_obj["symbol"]  = prefetched_data.get("symbol")

        elif "analysis" in prefetched_data and action == "text":
            response_obj["analysis"] = prefetched_data["analysis"]
            response_obj["symbol"]   = prefetched_data.get("symbol")

        # في حال لم يُرسل Gemini رسالة نصية، نبني رسالة غنية من بيانات التحليل الداخلية
        if not response_obj.get("message"):
            symbol = response_obj.get("symbol") or prefetched_data.get("symbol") or intent.get("symbol") or ""
            timeframe = response_obj.get("timeframe") or prefetched_data.get("timeframe") or intent.get("timeframe") or ""

            if action == "analyze" and "analysis" in prefetched_data:
                response_obj["message"] = self._build_analysis_summary(
                    prefetched_data["analysis"],
                    symbol or "Instrument",
                    timeframe or "1h",
                )
            elif action == "chart" and "candles" in prefetched_data:
                response_obj["message"] = (
                    f"تم تجهيز رسم الشموع لزوج {symbol or 'Instrument'} على فريم "
                    f"{timeframe or '1h'}. استخدم الرسم لقراءة حركة السعر وتأكيد التحليل."
                )
            elif action == "report" and "analysis" in prefetched_data:
                base = self._build_analysis_summary(
                    prefetched_data["analysis"],
                    symbol or "Instrument",
                    timeframe or "1h",
                )
                response_obj["message"] = "تقرير تداول مبني على التحليل الداخلي:\n\n" + base

        # احفظ رد الوكيل في التاريخ
        history.append({"role": "assistant", "content": response_obj.get("message", raw_response)})

        # حدّ التاريخ (آخر 20 رسالة)
        if len(history) > 20:
            self.sessions[session_id] = history[-20:]

        return response_obj


# Singleton
trading_agent = TradingChatAgent()
