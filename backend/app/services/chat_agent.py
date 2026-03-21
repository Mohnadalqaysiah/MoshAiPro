"""
Mosh AI Pro v5 - Trading Chat Agent (Professional)
====================================================
وكيل محادثة احترافي - لغة عامية طبيعية مع خبرة ICT/SMC كاملة
"""

import json
import aiohttp
from loguru import logger
from app.config import get_settings
from app.services.smart_data import smart_data

settings = get_settings()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ─── System Prompt ─────────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """
أنت "مُوش" — محلل تداول خبير بـ 15 سنة خبرة في ICT وSMC وWyckoff.
تتكلم بلغة عربية عامية مريحة وودية، مثل خبير يكلم صديقه.

═══ أسلوبك ═══
• استخدم عبارات مثل: "يا صديقي"، "شوف"، "الوضع هيك"، "الفرصة جيدة/مو جيدة"
• لا تكن رسمياً جداً ولا شبه رسالة بنكية
• لكن حافظ دايماً على دقة الأرقام والمستويات الفنية
• لا تتردد، قول رأيك بوضوح

═══ قواعد التحليل الصارمة ═══
1. دايماً أعطِ أرقام حقيقية من بيانات التحليل — لا placeholders ولا "غير محدد"
2. حتى لو التوصية WAIT: أعطِ مستويات مهمة للمراقبة (OB + FVG + liquidity)
3. لا ترسل JSON أبداً — فقط نص طبيعي
4. إذا عندك بيانات ICT: استخدمها (order blocks، FVG، BOS، kill zones)

═══ نموذج الرد للتحليل ═══

📊 **[الزوج] | [الإطار]**

السعر: [رقم] | التوصية: [شراء 📈 / بيع 📉 / انتظار ⏳] ([نسبة]% ثقة)

**الصورة العامة:**
[2-3 جمل بالعامية توضح وضع السوق — trend، هيكل، أهم مستوى]

**مستويات مهمة:**
• OB صاعد عند: [رقم] ← دعم قوي
• OB هابط عند: [رقم] ← مقاومة
• FVG: [رقم - رقم]
• سيولة (SSL/BSL): [رقم]

**إذا كانت التوصية شراء أو بيع:**
🎯 دخول مثالي: [رقم]
🛑 وقف: [رقم]
✅ هدف 1: [رقم]
✅ هدف 2: [رقم]
📐 R/R: 1:[رقم]

**إذا كانت التوصية انتظار:**
⏳ انتظر وصول السعر لـ [رقم] قبل الدخول
المنطقة اللي نتراقبها: [وصف]

⚠️ إدارة المخاطر مسؤوليتك.

═══ ملاحظات مهمة ═══
- إذا السوق مغلق: وضّح ذلك لكن أعطِ تحليل استرشادي
- لا تذكر "مُوش AI" أو "Gemini" في ردك
- إذا سألوا عن مفهوم ICT/SMC: اشرحه بمثال بسيط
"""


class TradingChatAgent:
    MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "ETHUSD"]

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key not in ("", "your_gemini_api_key_here"))
        self.sessions: dict[str, list] = {}
        self.session_context: dict[str, dict] = {}

    # ─── Intent Detection ───────────────────────────────────────────────────

    def _detect_intent(self, message: str, session_id: str) -> dict:
        msg = message.lower().strip()
        ctx = self.session_context.get(session_id, {})

        # ── كشف الرمز (عامية موسعة) ─────────────────────────────────────────
        symbol = None
        aliases = {
            "XAUUSD": [
                "ذهب", "الذهب", "ذهبي", "gold", "xau", "xauusd", "جولد",
                "xau/usd", "gold/usd",
            ],
            "BTCUSD": [
                "بيتكوين", "البيتكوين", "bitcoin", "btc", "btcusd", "بتكوين",
                "بتكونن", "البتكوين", "بيتكون", "عملة البيتكوين", "كوين",
                "btc/usd", "bitcoin/usd",
            ],
            "EURUSD": [
                "يورو", "اليورو", "euro", "eur", "eurusd", "eur/usd",
                "يورو دولار", "الأوروبي",
            ],
            "GBPUSD": [
                "جنيه", "الجنيه", "pound", "gbp", "gbpusd", "sterling",
                "gbp/usd", "جنيه إسترليني", "الإسترليني",
            ],
            "USDJPY": [
                "ين", "الين", "yen", "jpy", "usdjpy", "usd/jpy",
                "دولار ين", "الين الياباني",
            ],
            "USDCHF": [
                "فرنك", "الفرنك", "franc", "chf", "usdchf", "usd/chf",
                "فرنك سويسري",
            ],
            "ETHUSD": [
                "ايثريوم", "الايثريوم", "ethereum", "eth", "ethusd",
                "إيثيريوم", "إيث", "eth/usd",
            ],
        }
        for sym, words in aliases.items():
            if any(w in msg for w in words):
                symbol = sym
                break

        if not symbol:
            symbol = ctx.get("symbol")

        # ── كشف الإطار الزمني (عامية موسعة) ─────────────────────────────────
        timeframe = None

        if any(w in msg for w in ["1m", "دقيقة واحدة", "دقيقه واحده"]):
            timeframe = "1m"
        elif any(w in msg for w in ["5m", "5 دقيقة", "5 دقايق", "خمس دقايق", "خمس دقائق"]):
            timeframe = "5m"
        elif any(w in msg for w in [
            "15m", "15 دقيقة", "15 دقيقه", "15دقيقة", "ربع ساعة", "ربع ساعه",
            "عالـ15", "على 15", "على الـ 15", "15 دقايق",
        ]):
            timeframe = "15m"
        elif any(w in msg for w in [
            "30m", "30 دقيقة", "30 دقيقه", "نصف ساعة", "نص ساعة", "نص ساعه",
            "30 دقايق", "عالـ30",
        ]):
            timeframe = "30m"
        elif any(w in msg for w in [
            "4h", "4 ساعات", "4ساعات", "أربع ساعات", "اربع ساعات",
            "عالـ4", "على 4 ساعات",
        ]):
            timeframe = "4h"
        elif any(w in msg for w in [
            "يومي", "daily", "1d", "1day", "اليومي", "كل يوم",
        ]):
            timeframe = "1d"
        elif any(w in msg for w in [
            "ساعة", "ساعه", "1h", "ساعة واحدة", "عالـساعة", "على ساعة",
        ]):
            timeframe = "1h"

        # أرقام فقط
        stripped = msg.strip()
        if stripped in ["15", "30"]:
            timeframe = stripped + "m"
        elif stripped == "4":
            timeframe = "4h"
        elif stripped in ["1", "1h"]:
            timeframe = "1h"

        if not timeframe:
            timeframe = ctx.get("timeframe", "1h")

        # ── نوع الطلب ─────────────────────────────────────────────────────────
        is_analysis = any(w in msg for w in [
            "حلل", "تحليل", "analyze", "signal", "إشارة", "اشارة", "فرصة", "فرصه",
            "شراء", "بيع", "buy", "sell", "دخول", "entry", "توصية", "توصيه",
            "نقاط دخول", "اهداف", "أهداف", "وقف", "stop", "وين رح يروح",
            "وين السعر", "كيف الوضع", "ايش يقول", "شو رأيك", "رأيك بـ",
            "رايك", "ايه رأيك", "ايش تشوف", "وشو تشوف", "كيف تشوف",
            "فين السعر", "هل يرتفع", "هل ينزل", "رح يصعد", "رح ينزل",
            "مسير السعر", "اتجاه", "ترند",
        ])
        is_chart = any(w in msg for w in [
            "شموع", "رسم", "chart", "candlestick", "شمعة", "شارت", "شمعه"
        ])
        is_report = any(w in msg for w in [
            "تقرير", "report", "ملخص", "summary"
        ])
        is_greeting = any(w in msg for w in [
            "مرحبا", "مرحبى", "هلا", "اهلا", "أهلاً", "hi", "hello", "hey",
            "السلام", "يسعدك", "هلو", "صبح الخير", "صباح الخير", "مساء الخير",
            "هاي", "كيفك", "كيف حالك", "شلونك",
        ])
        is_explain = any(w in msg for w in [
            "شرح", "اشرح", "explain", "ما هو", "ما هي", "what is", "كيف",
            "معنى", "يعني ايش", "يعني شو", "ايش معنى", "شو يعني",
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
        try:
            from app.services.ai_engine_v5 import mosh_ai_engine_v5
            result = await mosh_ai_engine_v5.analyze_market(symbol, timeframe)
            return result
        except Exception as e:
            logger.error(f"Chat analysis error: {e}")
            return {}

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 60) -> list:
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
            f"السعر الحالي: {price}",
            f"التوصية: {rec} | الثقة: {conf:.1f}% | ATR: {atr}",
            f"السوق: {'مفتوح' if market_open else 'مغلق'}",
            "",
            f"هيكل السوق: {structure.get('trend','?')} ({structure.get('structure','?')})",
            f"آخر BOS: {structure.get('last_bos',{})}",
            "",
            f"Order Blocks صاعدة (دعم): {ob.get('bullish_obs',[])}",
            f"السعر داخل OB صاعد: {ob.get('in_bullish_ob',False)}",
            f"Order Blocks هابطة (مقاومة): {ob.get('bearish_obs',[])}",
            f"السعر داخل OB هابط: {ob.get('in_bearish_ob',False)}",
            "",
            f"FVG صاعد: {fvg_d.get('bullish_fvgs',[])}",
            f"FVG هابط: {fvg_d.get('bearish_fvgs',[])}",
            "",
            f"سيولة BSL (فوق): {liq.get('nearest_bsl','?')}",
            f"سيولة SSL (تحت): {liq.get('nearest_ssl','?')}",
            "",
            f"منطقة Premium/Discount: {pd_z.get('zone','?')} ({pd_z.get('pct',0):.1f}%)",
            f"OTE (61.8%): {pd_z.get('ote_level','?')}",
            f"Equilibrium (50%): {pd_z.get('equilibrium','?')}",
            "",
            f"Kill Zone: {kz.get('active_session','?')} | وقت مثالي: {kz.get('is_optimal_time',False)}",
            f"Wyckoff: {wyckoff.get('phase','?')} ← {wyckoff.get('action','?')}",
            "",
            f"RSI: {indicators.get('rsi',0):.1f}",
            f"MACD: {indicators.get('macd',0)}",
            f"EMA20: {indicators.get('ema_20',0)}",
            f"EMA50: {indicators.get('ema_50',0)}",
            f"EMA200: {indicators.get('ema_200',0)}",
            "",
            f"عوامل Confluence المؤكدة: {confluence.get('factors',[])}",
            f"عدد العوامل: {confluence.get('factor_count',0)}/9",
            f"درجة Confluence: {confluence.get('score',0)}",
            "",
            f"نقاط الدخول المقترحة: {entry}",
            f"وقف الخسارة: {sl}",
            f"الأهداف: {tps}",
            f"R/R: 1:{rr}",
        ]

        if gemini_a.get("enabled"):
            lines += [
                "",
                f"تقييم Gemini: {rec} ({gemini_a.get('confidence',0)}%)",
                f"Grade: {gemini_a.get('signal_grade','?')}",
                f"Setup: {gemini_a.get('ict_setup','')}",
                f"السبب: {gemini_a.get('primary_reason','')}",
                f"الملخص: {gemini_a.get('arabic_summary','')}",
                f"التأكيدات: {gemini_a.get('confirmations',[])}",
                f"التحذيرات: {gemini_a.get('warnings',[])}",
            ]

        return "\n".join(str(l) for l in lines)

    # ─── Fallback (no Gemini) ────────────────────────────────────────────────

    def _build_direct_response(self, analysis: dict, symbol: str, timeframe: str, is_chart: bool = False) -> dict:
        """بناء رد مباشر بأرقام حقيقية - يعمل حتى بدون Gemini"""
        if not analysis:
            return {
                "action": "text",
                "message": f"⚠️ ما قدرت أجيب تحليل {symbol}. تحقق من الاتصال."
            }

        market_open = analysis.get("market_open", True)
        rec = analysis.get("recommendation", "WAIT")
        conf = analysis.get("ai_confidence_score", 0)
        price = analysis.get("current_price", 0)
        atr = analysis.get("atr", 0)
        entry = analysis.get("entry_zones", [])
        sl = analysis.get("stop_loss_zone", 0)
        tps = analysis.get("take_profit_zones", [])
        rr = analysis.get("risk_reward_ratio", 0)
        confluence = analysis.get("confluence", {})
        factors = confluence.get("factors", [])
        structure = analysis.get("market_structure", {})
        pd_z = analysis.get("premium_discount", {})
        kz = analysis.get("kill_zone", {})
        ob = analysis.get("order_blocks", {})
        fvg_d = analysis.get("fvg", {})
        liq = analysis.get("liquidity", {})
        gemini_a = analysis.get("gemini_analysis", {})
        indicators = analysis.get("indicators", {})

        rec_emoji = {"BUY": "📈", "SELL": "📉", "WAIT": "⏳", "WATCH": "👁️"}.get(rec, "⏳")
        rec_ar    = {"BUY": "شراء", "SELL": "بيع", "WAIT": "انتظار", "WATCH": "مراقبة"}.get(rec, rec)

        closed_note = "\n⛔ **السوق مغلق حالياً** — التحليل استرشادي فقط.\n" if not market_open else ""

        lines = [
            f"📊 **{symbol} | {timeframe}**",
            closed_note,
            f"💰 السعر: **{price}**",
            f"{rec_emoji} **{rec_ar}** | الثقة: **{conf:.1f}%**",
            f"🏗️ {structure.get('trend','?')} ({structure.get('structure','?')})",
            f"📍 منطقة: {pd_z.get('zone','?')} ({pd_z.get('pct',0):.1f}%)",
            f"⏰ {kz.get('active_session','?')} {'🎯 Kill Zone مثالي' if kz.get('is_optimal_time') else ''}",
            "",
        ]

        # مستويات مهمة - دايماً تظهر
        important_levels = []
        bull_obs = ob.get("bullish_obs", [])
        bear_obs  = ob.get("bearish_obs", [])
        bull_fvgs = fvg_d.get("bullish_fvgs", [])
        bear_fvgs = fvg_d.get("bearish_fvgs", [])
        bsl = liq.get("nearest_bsl")
        ssl = liq.get("nearest_ssl")
        ote = pd_z.get("ote_level")
        eq = pd_z.get("equilibrium")

        if bull_obs:
            important_levels.append(f"🟢 OB دعم: **{bull_obs[0] if isinstance(bull_obs[0], (int, float)) else bull_obs[0]}**")
        if bear_obs:
            important_levels.append(f"🔴 OB مقاومة: **{bear_obs[0] if isinstance(bear_obs[0], (int, float)) else bear_obs[0]}**")
        if bull_fvgs:
            fvg = bull_fvgs[0]
            if isinstance(fvg, dict):
                important_levels.append(f"💠 FVG صاعد: **{fvg.get('low','?')} - {fvg.get('high','?')}**")
        if bear_fvgs:
            fvg = bear_fvgs[0]
            if isinstance(fvg, dict):
                important_levels.append(f"💠 FVG هابط: **{fvg.get('low','?')} - {fvg.get('high','?')}**")
        if ssl:
            important_levels.append(f"🧲 سيولة تحت (SSL): **{ssl}**")
        if bsl:
            important_levels.append(f"🧲 سيولة فوق (BSL): **{bsl}**")
        if ote:
            important_levels.append(f"📐 OTE (61.8%): **{ote}**")
        if eq:
            important_levels.append(f"⚖️ Equilibrium: **{eq}**")

        if important_levels:
            lines.append("**مستويات مهمة:**")
            lines.extend(important_levels)
            lines.append("")

        # مستويات الدخول
        if rec in ["BUY", "SELL"] and entry:
            lines += [
                "**مستويات التداول:**",
                f"🎯 دخول: **{entry[0]}**",
                f"🛑 وقف الخسارة: **{sl}**" if sl else "",
                f"✅ هدف 1: **{tps[0]}**" if len(tps) > 0 else "",
                f"✅ هدف 2: **{tps[1]}**" if len(tps) > 1 else "",
                f"✅ هدف 3: **{tps[2]}**" if len(tps) > 2 else "",
                f"📐 R/R: **1:{rr:.1f}**" if rr else "",
                "",
            ]
        elif rec == "WAIT":
            # للانتظار: أعطِ المنطقة اللي نتراقبها
            watch_zone = ""
            if bull_obs and structure.get("trend", "").upper() in ["BULLISH", "UP"]:
                watch_zone = f"انتظر وصول السعر لمنطقة الـ OB عند **{bull_obs[0]}** قبل الدخول"
            elif bear_obs and structure.get("trend", "").upper() in ["BEARISH", "DOWN"]:
                watch_zone = f"انتظر وصول السعر لمنطقة الـ OB عند **{bear_obs[0]}** قبل البيع"
            elif eq:
                watch_zone = f"انتظر وضوح الاتجاه من عند Equilibrium **{eq}**"

            if watch_zone:
                lines += [
                    "**ماذا ننتظر؟**",
                    f"⏳ {watch_zone}",
                    "",
                ]

        if factors:
            lines.append("**عوامل التأكيد:**")
            for f in factors[:4]:
                lines.append(f"• {f}")
            lines.append("")

        if gemini_a.get("enabled") and gemini_a.get("arabic_summary"):
            lines += [
                "**رأي المحلل:**",
                gemini_a.get("arabic_summary", ""),
                "",
            ]

        lines.append("⚠️ للمعلومات فقط، إدارة المخاطر مسؤوليتك.")

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
        for msg in messages[-14:]:
            history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })

        system = AGENT_SYSTEM_PROMPT
        if system_extra:
            system += f"\n\n══════════════════\nبيانات التحليل (استخدم هذه الأرقام بالضبط):\n{system_extra}"

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": history,
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 1800,
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
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        if session_id not in self.session_context:
            self.session_context[session_id] = {}

        history = self.sessions[session_id]
        context = self.session_context[session_id]
        history.append({"role": "user", "content": user_message})

        intent = self._detect_intent(user_message, session_id)

        if intent["symbol"]:
            context["symbol"] = intent["symbol"]
        if intent["timeframe"]:
            context["timeframe"] = intent["timeframe"]
        self.session_context[session_id] = context

        symbol    = intent["symbol"]
        timeframe = intent["timeframe"]

        # ── تحية ──────────────────────────────────────────────────────────────
        if intent["is_greeting"] and not intent["is_analysis"] and not symbol:
            msg = (
                "👋 هلا! أنا مُوش، محللك في أسواق الـ ICT/SMC.\n\n"
                "قولي أي زوج تبي أحلله وبأي إطار زمني، وأنا أعطيك:\n"
                "📊 التحليل الكامل مع نقاط الدخول والأهداف\n"
                "🕯️ شموع يابانية مباشرة\n"
                "📐 Order Blocks, FVG, سيولة\n\n"
                "مثال: *حلل البتكوين 15 دقيقة* 🚀"
            )
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        # ── شرح مفهوم ────────────────────────────────────────────────────────
        if intent["is_explain"] and not intent["is_analysis"]:
            raw = await self._call_gemini(history)
            msg = raw.strip() if raw else "اسألني عن أي مفهوم: Order Blocks, FVG, BOS, CHoCH, Kill Zones, Wyckoff..."
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        # ── رسالة عامة بدون رمز ──────────────────────────────────────────────
        needs_analysis = intent["is_analysis"] or intent["is_report"] or intent["is_chart"]
        if not needs_analysis and not symbol:
            raw = await self._call_gemini(history)
            msg = raw.strip() if raw else "حدد الزوج الذي تريد تحليله (مثل: ذهب، بتكوين، يورو)"
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        if not symbol:
            symbol = "XAUUSD"

        # ── جلب البيانات ────────────────────────────────────────────────────
        logger.info(f"🔍 Chat: تحليل {symbol} {timeframe}")
        analysis = await self._fetch_analysis(symbol, timeframe)
        candles = []
        if intent["is_chart"]:
            candles = await self._fetch_candles(symbol, timeframe, limit=60)

        # ── رد مع Gemini ─────────────────────────────────────────────────────
        if self.enabled and analysis:
            extra_ctx = self._build_analysis_context(analysis, symbol, timeframe)
            if candles:
                extra_ctx += f"\n\nبيانات الشموع متوفرة ({len(candles)} شمعة)"

            raw = await self._call_gemini(history, extra_ctx)

            if raw and raw.strip():
                clean = raw.strip()
                # تنظيف JSON إذا أرجع Gemini JSON بالغلط
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
