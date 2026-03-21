"""
Mosh AI Pro v5 - Trading Chat Agent (Professional)
====================================================
وكيل محادثة احترافي يعمل مباشرة مع ICT Engine
- لا أسئلة زائدة
- ردود عربية طبيعية واضحة مع أرقام حقيقية
- يفحص حالة السوق
- يتذكر السياق في الجلسة
"""

import json
import aiohttp
from loguru import logger
from app.config import get_settings
from app.services.smart_data import smart_data

settings = get_settings()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ─── System Prompt الاحترافي ─────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """
أنت "مُوش" - مساعد تداول احترافي خبير بمدارس ICT/SMC/Wyckoff.

قواعد الرد الصارمة:
═══════════════════
1. لا تسأل أسئلة إضافية أبداً - استخدم القيم الافتراضية (الإطار الافتراضي = 1h)
2. إذا توفر تحليل في السياق → اشرحه مباشرة بأرقام حقيقية من البيانات
3. لا تكتب placeholders مثل [أدخل السعر هنا] أو [من بيانات التحليل] - إما أرقام حقيقية أو لا تذكر الحقل
4. ردودك بالعربية الواضحة، أسلوب خبير موجز ومباشر
5. استخدم الرموز التعبيرية بحكمة لتوضيح النقاط (📈 للشراء، 📉 للبيع، ⚠️ للتحذير)
6. لا ترسل JSON أبداً - فقط نص عربي طبيعي

نموذج الرد لتحليل السوق:
═══════════════════════════
📊 **تحليل [الزوج] - [الإطار الزمني]**

السعر الحالي: [رقم]
التوصية: [شراء/بيع/انتظار] | الثقة: [رقم]%

**الـ Setup:**
- [اذكر Setup ICT الحالي مثل: OB Retest + FVG Fill]

**مستويات التداول:**
🎯 دخول: [رقم]
🛑 وقف الخسارة: [رقم]
✅ هدف 1: [رقم]
✅ هدف 2: [رقم]
📐 R/R: 1:[رقم]

**عوامل التأكيد:**
• [عامل 1]
• [عامل 2]
• [عامل 3]

⚠️ [تحذير إن وجد]

لا تنس دائماً: هذا تحليل تعليمي، إدارة المخاطر مسؤوليتك.

إذا السوق مغلق: وضّح ذلك واعطِ تحليلاً استرشادياً فقط.
إذا لا توجد فرصة واضحة: قل ذلك بوضوح وشرح لماذا.
"""


class TradingChatAgent:
    MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "ETHUSD"]

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key not in ("", "your_gemini_api_key_here"))
        self.sessions: dict[str, list] = {}
        self.session_context: dict[str, dict] = {}  # يحفظ آخر رمز وإطار زمني

    # ─── Intent Detection ───────────────────────────────────────────────────

    def _detect_intent(self, message: str, session_id: str) -> dict:
        msg = message.lower()
        ctx = self.session_context.get(session_id, {})

        # كشف الرمز
        symbol = None
        aliases = {
            "XAUUSD": ["ذهب", "gold", "xau", "xauusd"],
            "BTCUSD": ["بيتكوين", "bitcoin", "btc", "btcusd"],
            "EURUSD": ["يورو", "euro", "eur", "eurusd"],
            "GBPUSD": ["جنيه", "pound", "gbp", "gbpusd"],
            "USDJPY": ["ين", "yen", "jpy", "usdjpy"],
            "USDCHF": ["فرنك", "franc", "chf", "usdchf"],
            "ETHUSD": ["ايثريوم", "ethereum", "eth", "ethusd"],
        }
        for sym, words in aliases.items():
            if any(w in msg for w in words):
                symbol = sym
                break

        # استخدم الرمز من الجلسة إذا لم يُذكر
        if not symbol:
            symbol = ctx.get("symbol")

        # كشف الإطار الزمني
        timeframe = None
        if any(w in msg for w in ["15m", "15 دقيقة", "15دقيقة", "ربع ساعة", " 15"]):
            timeframe = "15m"
        elif any(w in msg for w in ["30m", "30 دقيقة", "نصف ساعة"]):
            timeframe = "30m"
        elif any(w in msg for w in ["4h", "4 ساعات", "أربع ساعات", "4ساعات"]):
            timeframe = "4h"
        elif any(w in msg for w in ["يومي", "daily", "1d", "1day"]):
            timeframe = "1d"
        elif any(w in msg for w in ["ساعة", "1h", " 1 "]) or msg.strip() in ["1", "1h"]:
            timeframe = "1h"

        if not timeframe:
            timeframe = ctx.get("timeframe", "1h")

        # أرقام فقط = إطار زمني
        if msg.strip() in ["15", "30"]:
            timeframe = msg.strip() + "m"
        elif msg.strip() in ["4"]:
            timeframe = "4h"
        elif msg.strip() in ["1"]:
            timeframe = "1h"

        is_analysis = any(w in msg for w in [
            "حلل", "تحليل", "analyze", "signal", "إشارة", "فرصة",
            "شراء", "بيع", "buy", "sell", "دخول", "entry", "توصية",
            "نقاط دخول", "اهداف", "وقف", "stop"
        ])
        is_chart = any(w in msg for w in [
            "شموع", "رسم", "chart", "candlestick", "شمعة", "شارت"
        ])
        is_report = any(w in msg for w in [
            "تقرير", "report", "ملخص", "summary"
        ])
        is_greeting = any(w in msg for w in [
            "مرحبا", "هلا", "اهلا", "hi", "hello", "hey", "السلام"
        ])
        is_explain = any(w in msg for w in [
            "شرح", "explain", "ما هو", "what is", "كيف", "معنى"
        ])

        # إذا ذُكر رمز وحده = تحليل
        if symbol and not is_analysis and not is_chart and not is_report:
            is_analysis = True

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "is_analysis": is_analysis,
            "is_chart": is_chart,
            "is_report": is_report,
            "is_greeting": is_greeting,
            "is_explain": is_explain,
        }

    # ─── Data Fetching ───────────────────────────────────────────────────────

    async def _fetch_analysis(self, symbol: str, timeframe: str) -> dict:
        """يستدعي المحرك مباشرة (أسرع من HTTP)"""
        try:
            from app.services.ai_engine_v5 import mosh_ai_engine_v5
            result = await mosh_ai_engine_v5.analyze_market(symbol, timeframe)
            return result
        except Exception as e:
            logger.error(f"Chat analysis error: {e}")
            return {}

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 60) -> list:
        """جلب الشموع عبر smart_data"""
        try:
            df = await smart_data.get_ohlcv(symbol, timeframe, bars=limit)
            if df is None:
                return []
            candles = []
            for _, row in df.tail(limit).iterrows():
                dt = row.get("datetime", row.name)
                try:
                    ts = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
                except:
                    ts = str(dt)
                candles.append({
                    "time": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0)),
                })
            return candles
        except Exception as e:
            logger.error(f"Chat candles error: {e}")
            return []

    # ─── Context Builder ─────────────────────────────────────────────────────

    def _build_analysis_context(self, analysis: dict, symbol: str, timeframe: str) -> str:
        """يبني سياقاً غنياً بالأرقام الحقيقية لـ Gemini"""
        if not analysis or analysis.get("error"):
            return f"فشل جلب تحليل {symbol}"

        rec = analysis.get("recommendation", "WAIT")
        conf = analysis.get("ai_confidence_score", 0)
        price = analysis.get("current_price", 0)
        atr = analysis.get("atr", 0)
        entry = analysis.get("entry_zones", [])
        sl = analysis.get("stop_loss_zone", 0)
        tps = analysis.get("take_profit_zones", [])
        rr = analysis.get("risk_reward_ratio", 0)

        structure = analysis.get("market_structure", {})
        ob = analysis.get("order_blocks", {})
        fvg_d = analysis.get("fvg", {})
        liq = analysis.get("liquidity", {})
        pd_z = analysis.get("premium_discount", {})
        kz = analysis.get("kill_zone", {})
        wyckoff = analysis.get("wyckoff", {})
        confluence = analysis.get("confluence", {})
        indicators = analysis.get("indicators", {})
        gemini_a = analysis.get("gemini_analysis", {})
        market_open = analysis.get("market_open", True)

        lines = [
            f"═══ تحليل {symbol} على {timeframe} ═══",
            f"السعر الحالي: {price:.5f}",
            f"التوصية: {rec} | الثقة: {conf:.1f}% | ATR: {atr:.5f}",
            f"السوق: {'مفتوح ✅' if market_open else 'مغلق ⛔'}",
            "",
            f"هيكل السوق: {structure.get('trend','?')} ({structure.get('structure','?')})",
            f"BOS: {structure.get('last_bos',{})}",
            "",
            f"Order Blocks صاعدة: {ob.get('bullish_obs',[])}",
            f"في OB صاعد: {ob.get('in_bullish_ob',False)}",
            f"Order Blocks هابطة: {ob.get('bearish_obs',[])}",
            f"في OB هابط: {ob.get('in_bearish_ob',False)}",
            "",
            f"FVG صاعد: {fvg_d.get('bullish_fvgs',[])}",
            f"FVG هابط: {fvg_d.get('bearish_fvgs',[])}",
            "",
            f"السيولة BSL: {liq.get('nearest_bsl','?')}",
            f"السيولة SSL: {liq.get('nearest_ssl','?')}",
            "",
            f"منطقة Premium/Discount: {pd_z.get('zone','?')} ({pd_z.get('pct',0):.1f}%)",
            f"OTE (61.8%): {pd_z.get('ote_level','?')}",
            f"Equilibrium: {pd_z.get('equilibrium','?')}",
            "",
            f"Kill Zone: {kz.get('active_session','?')} | مثالي: {kz.get('is_optimal_time',False)}",
            f"Wyckoff: {wyckoff.get('phase','?')} → {wyckoff.get('action','?')}",
            "",
            f"RSI: {indicators.get('rsi',0):.1f}",
            f"MACD: {indicators.get('macd',0):.5f}",
            f"EMA20: {indicators.get('ema_20',0):.5f}",
            f"EMA50: {indicators.get('ema_50',0):.5f}",
            "",
            f"عوامل Confluence: {confluence.get('factors',[])}",
            f"عدد العوامل: {confluence.get('factor_count',0)}",
            "",
            f"نقاط الدخول: {entry}",
            f"وقف الخسارة: {sl}",
            f"الأهداف: {tps}",
            f"R/R: 1:{rr}",
            "",
        ]

        if gemini_a.get("enabled"):
            lines += [
                f"تحليل Gemini: {rec} ({gemini_a.get('confidence',0)}%)",
                f"Grade: {gemini_a.get('signal_grade','?')}",
                f"Setup: {gemini_a.get('ict_setup','')}",
                f"السبب: {gemini_a.get('primary_reason','')}",
                f"الملخص: {gemini_a.get('arabic_summary','')}",
                f"التأكيدات: {gemini_a.get('confirmations',[])}",
                f"التحذيرات: {gemini_a.get('warnings',[])}",
            ]

        return "\n".join(lines)

    # ─── Fallback (no Gemini) ────────────────────────────────────────────────

    def _build_direct_response(self, analysis: dict, symbol: str, timeframe: str, is_chart: bool = False) -> dict:
        """بناء رد مباشر بدون Gemini - بأرقام حقيقية"""
        if not analysis:
            return {
                "action": "text",
                "message": f"⚠️ لم أتمكن من جلب تحليل {symbol}. تحقق من الاتصال بالإنترنت."
            }

        market_open = analysis.get("market_open", True)
        rec = analysis.get("recommendation", "WAIT")
        conf = analysis.get("ai_confidence_score", 0)
        price = analysis.get("current_price", 0)
        entry = analysis.get("entry_zones", [])
        sl = analysis.get("stop_loss_zone", 0)
        tps = analysis.get("take_profit_zones", [])
        rr = analysis.get("risk_reward_ratio", 0)
        confluence = analysis.get("confluence", {})
        factors = confluence.get("factors", [])
        structure = analysis.get("market_structure", {})
        pd_z = analysis.get("premium_discount", {})
        kz = analysis.get("kill_zone", {})
        gemini_a = analysis.get("gemini_analysis", {})

        rec_emoji = {"BUY": "📈", "SELL": "📉", "WAIT": "⏳", "WATCH": "👁️"}.get(rec, "⏳")
        rec_ar = {"BUY": "شراء", "SELL": "بيع", "WAIT": "انتظار", "WATCH": "مراقبة"}.get(rec, rec)

        closed_note = "\n⛔ **تنبيه: السوق حالياً مغلق** - هذا تحليل استرشادي فقط.\n" if not market_open else ""

        lines = [
            f"📊 **تحليل {symbol} على {timeframe}**",
            closed_note,
            f"💰 السعر الحالي: **{price:.5f}**",
            f"{rec_emoji} التوصية: **{rec_ar}** | الثقة: **{conf:.1f}%**",
            f"🏗️ هيكل السوق: {structure.get('trend','?')} ({structure.get('structure','?')})",
            f"📍 منطقة: {pd_z.get('zone','?')} ({pd_z.get('pct',0):.1f}%)",
            f"⏰ {kz.get('active_session','?')} | {'Kill Zone مثالي ✅' if kz.get('is_optimal_time') else 'خارج وقت مثالي'}",
            "",
        ]

        if rec in ["BUY", "SELL"] and entry:
            lines += [
                "**مستويات التداول:**",
                f"🎯 دخول: **{entry[0]:.5f}**",
                f"🛑 وقف الخسارة: **{sl:.5f}**" if sl else "",
                f"✅ هدف 1: **{tps[0]:.5f}**" if len(tps) > 0 else "",
                f"✅ هدف 2: **{tps[1]:.5f}**" if len(tps) > 1 else "",
                f"✅ هدف 3: **{tps[2]:.5f}**" if len(tps) > 2 else "",
                f"📐 R/R: **1:{rr:.1f}**" if rr else "",
                "",
            ]

        if factors:
            lines.append("**عوامل التأكيد:**")
            for f in factors[:4]:
                lines.append(f"• {f}")
            lines.append("")

        if gemini_a.get("enabled") and gemini_a.get("arabic_summary"):
            lines += [
                "**🤖 تحليل مُوش AI:**",
                gemini_a.get("arabic_summary", ""),
                "",
            ]

        lines.append("⚠️ هذا تحليل تعليمي وليس نصيحة استثمارية. إدارة المخاطر مسؤوليتك.")

        return {
            "action": "chart" if is_chart else "analyze",
            "message": "\n".join(l for l in lines if l is not None),
            "symbol": symbol,
            "timeframe": timeframe,
        }

    # ─── Gemini Call ─────────────────────────────────────────────────────────

    async def _call_gemini(self, messages: list, system_extra: str = "") -> str:
        if not self.enabled:
            return ""

        history = []
        for msg in messages[-12:]:
            history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })

        system = AGENT_SYSTEM_PROMPT
        if system_extra:
            system += f"\n\n══════════════════\nبيانات التحليل الحالية (استخدمها للأرقام):\n{system_extra}"

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": history,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1500,
            }
        }

        try:
            async with aiohttp.ClientSession() as sess:
                url = f"{GEMINI_URL}?key={self.api_key}"
                async with sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Gemini chat {resp.status}: {body[:200]}")
                        return ""
                    data = await resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return ""

    # ─── Main Chat ───────────────────────────────────────────────────────────

    async def chat(self, session_id: str, user_message: str) -> dict:
        """
        معالجة رسالة وإرجاع الرد

        Returns: {
            "action": "text|analyze|chart|report",
            "message": "نص عربي طبيعي",
            "symbol": "...",
            "timeframe": "...",
            "data": {...}  # التحليل أو الشموع
        }
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        if session_id not in self.session_context:
            self.session_context[session_id] = {}

        history = self.sessions[session_id]
        context = self.session_context[session_id]
        history.append({"role": "user", "content": user_message})

        intent = self._detect_intent(user_message, session_id)

        # تحديث سياق الجلسة
        if intent["symbol"]:
            context["symbol"] = intent["symbol"]
        if intent["timeframe"]:
            context["timeframe"] = intent["timeframe"]
        self.session_context[session_id] = context

        symbol = intent["symbol"]
        timeframe = intent["timeframe"]

        # ── تحية ──────────────────────────────────────────────────────────────
        if intent["is_greeting"] and not intent["is_analysis"] and not symbol:
            msg = (
                "👋 أهلاً! أنا مُوش، مساعدك في تداول ICT/SMC.\n\n"
                "يمكنني:\n"
                "📊 تحليل الأزواج مع نقاط الدخول والأهداف\n"
                "🕯️ عرض شموع يابانية مباشرة\n"
                "📋 إعداد تقارير تداول مفصلة\n"
                "📚 شرح مفاهيم ICT/SMC/Wyckoff\n\n"
                "مثال: *حلل لي الذهب XAUUSD على ساعة*"
            )
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        # ── شرح مفهوم ────────────────────────────────────────────────────────
        if intent["is_explain"] and not intent["is_analysis"]:
            raw = await self._call_gemini(history)
            msg = raw.strip() if raw else "يمكنك سؤالي عن Order Blocks, FVG, BOS, CHoCH, Wyckoff, Kill Zones."
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        # ── تحليل / شموع / تقرير ─────────────────────────────────────────────
        needs_analysis = intent["is_analysis"] or intent["is_report"] or intent["is_chart"]

        if not needs_analysis and not symbol:
            # رسالة عامة بدون رمز محدد
            raw = await self._call_gemini(history)
            msg = raw.strip() if raw else "حدد الزوج الذي تريد تحليله (مثل: XAUUSD, BTCUSD, EURUSD)"
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        if not symbol:
            symbol = "XAUUSD"  # افتراضي

        # فحص السوق
        market_open = smart_data.is_market_open(symbol)

        # جلب التحليل
        analysis = {}
        candles = []

        if needs_analysis or symbol:
            logger.info(f"🔍 Chat: تحليل {symbol} {timeframe}")
            analysis = await self._fetch_analysis(symbol, timeframe)

        if intent["is_chart"]:
            logger.info(f"🕯️ Chat: شموع {symbol} {timeframe}")
            candles = await self._fetch_candles(symbol, timeframe, limit=60)

        # ── رد مع Gemini ────────────────────────────────────────────────────
        if self.enabled and analysis:
            extra_ctx = self._build_analysis_context(analysis, symbol, timeframe)
            if candles:
                extra_ctx += f"\n\nبيانات الشموع متوفرة ({len(candles)} شمعة للعرض)"

            raw = await self._call_gemini(history, extra_ctx)

            if raw and raw.strip():
                # إذا Gemini أعاد JSON بالغلط، نحوّله لنص
                clean = raw.strip()
                if clean.startswith("{") or "```json" in clean:
                    try:
                        if "```json" in clean:
                            clean = clean.split("```json")[1].split("```")[0].strip()
                        obj = json.loads(clean)
                        msg = obj.get("message", clean)
                    except:
                        msg = clean
                else:
                    msg = clean

                action = "chart" if intent["is_chart"] else "report" if intent["is_report"] else "analyze"
                reply = {
                    "action": action,
                    "message": msg,
                    "symbol": symbol,
                    "timeframe": timeframe,
                }
                if analysis:
                    reply["data"] = analysis
                if candles:
                    reply["candles"] = candles

                history.append({"role": "assistant", "content": msg})
                if len(history) > 20:
                    self.sessions[session_id] = history[-20:]
                return reply

        # ── رد مباشر بدون Gemini ─────────────────────────────────────────────
        reply = self._build_direct_response(analysis, symbol, timeframe, intent["is_chart"])

        if analysis:
            reply["data"] = analysis
        if candles:
            reply["candles"] = candles
            reply["action"] = "chart"

        history.append({"role": "assistant", "content": reply["message"]})
        if len(history) > 20:
            self.sessions[session_id] = history[-20:]

        return reply


# Singleton
trading_agent = TradingChatAgent()
