"""
Qaffel AI — Public Chat (Landing Page)
محادثة عامة بدون تسجيل، محدودة بـ 5 رسائل، تعرض تحليلاً مشفراً

(2026-09-21) اسم الودجت «تحليل ذكي» / Smart Analysis، والردود الثابتة تتبع
`lang` الآتي من واجهة الموقع (ar افتراضياً).
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from loguru import logger

router = APIRouter()

# كاش بسيط في الذاكرة للجلسات (session_id → count)
_session_counts: dict = {}
MAX_FREE_MESSAGES = 5


class PublicChatIn(BaseModel):
    message: str
    session_id: str  # UUID من الفرونتند
    lang: str = "ar"  # لغة واجهة الموقع — تحدد لغة الردود الثابتة فقط


@router.post("/chat")
async def public_chat(data: PublicChatIn):
    sid   = data.session_id[:64]
    count = _session_counts.get(sid, 0)
    en    = data.lang == "en"

    if count >= MAX_FREE_MESSAGES:
        return {
            "action": "register_cta",
            "message": (
                "🔒 You've used your 5 free chats.\n\n"
                "Sign up now for full access to Smart Analysis:\n"
                "✅ Unlimited analyses\n"
                "✅ Full entry signals\n"
                "✅ Precise TP & SL\n"
                "✅ Instant Telegram alerts"
            ) if en else (
                "🔒 استهلكت محادثاتك المجانية الخمس.\n\n"
                "سجّل الآن للوصول الكامل لـ «تحليل ذكي»:\n"
                "✅ تحليلات غير محدودة\n"
                "✅ إشارات دخول كاملة\n"
                "✅ TP وSL دقيقة\n"
                "✅ تنبيهات فورية على تيليجرام"
            ),
            "messages_used": count,
            "messages_limit": MAX_FREE_MESSAGES,
        }

    _session_counts[sid] = count + 1
    remaining = MAX_FREE_MESSAGES - count - 1

    msg = data.message.lower()

    # كشف طلب تحليل
    analysis_words = ["حلل","تحليل","analyze","analyse","signal","اشتري","ابيع","بيع","شراء",
                      "توصية","recommendation","entry","دخول","سعر","price","outlook"]
    wants_analysis = any(w in msg for w in analysis_words)

    # كشف رمز
    symbol_map = {
        "ذهب":"XAUUSD","gold":"XAUUSD","xauusd":"XAUUSD",
        "بيتكوين":"BTCUSD","bitcoin":"BTCUSD","btc":"BTCUSD",
        "يورو":"EURUSD","euro":"EURUSD","eurusd":"EURUSD",
        "جنيه":"GBPUSD","pound":"GBPUSD","gbpusd":"GBPUSD",
        "نازداك":"NAS100","nasdaq":"NAS100","nas100":"NAS100",
        "نفط":"USOIL","oil":"USOIL","usoil":"USOIL",
        "فضة":"XAGUSD","silver":"XAGUSD",
    }
    symbol = next((v for k, v in symbol_map.items() if k in msg), None)

    if wants_analysis and symbol:
        try:
            from app.services.ai_engine_v5 import mosh_ai_engine_v5
            analysis = await mosh_ai_engine_v5.analyze_market(symbol, "1h")
            rec   = analysis.get("recommendation", "WAIT")
            conf  = analysis.get("ai_confidence_score", 0)
            price = analysis.get("current_price", 0)

            if en:
                rec_l = {"BUY":"📈 Buy","SELL":"📉 Sell","WAIT":"⏳ Wait"}.get(rec, rec)
                msg_text = (
                    f"📊 **{symbol} | 1H**\n"
                    f"Direction: **{rec_l}**\n"
                    f"Confidence: **{conf:.0f}%**\n"
                    f"Price: **{price}**\n\n"
                    f"🔒 **Entry levels and targets are locked**\n"
                    f"Sign up free for full access to:\n"
                    f"• Exact entry point\n"
                    f"• Stop loss (SL)\n"
                    f"• Targets TP1 & TP2\n"
                    f"• Instant Telegram alerts"
                )
            else:
                rec_ar = {"BUY":"📈 شراء","SELL":"📉 بيع","WAIT":"⏳ انتظار"}.get(rec, rec)
                msg_text = (
                    f"📊 **{symbol} | 1H**\n"
                    f"الاتجاه: **{rec_ar}**\n"
                    f"الثقة: **{conf:.0f}%**\n"
                    f"السعر: **{price}**\n\n"
                    f"🔒 **مستويات الدخول والأهداف مشفرة**\n"
                    f"سجّل مجاناً للوصول الكامل لـ:\n"
                    f"• نقطة الدخول الدقيقة\n"
                    f"• وقف الخسارة (SL)\n"
                    f"• الأهداف TP1 و TP2\n"
                    f"• تنبيهات تيليجرام فورية"
                )
            return {
                "action": "locked_analysis",
                "message": msg_text,
                "symbol": symbol,
                "direction": rec,
                "confidence": conf,
                "messages_left": remaining,
            }
        except Exception as e:
            logger.warning(f"Public chat analysis error: {e}")

    # ردود عامة بسيطة
    greetings = ["مرحبا","هلا","hi","hello","السلام","اهلا","هاي"]
    if any(w in msg for w in greetings):
        reply = (
            f"Hi! I'm Smart Analysis — the AI market analyst from Qaffel AI 👋\n\n"
            f"I can analyze Gold, Bitcoin, Forex, NASDAQ and Oil.\n"
            f"Try: 'Analyze Gold' or 'What about Bitcoin?'\n\n"
            f"You have **{remaining + 1}** free chats left."
        ) if en else (
            f"أهلاً! أنا «تحليل ذكي» — محلّل الأسواق بالذكاء الاصطناعي من Qaffel AI 👋\n\n"
            f"أستطيع تحليل الذهب، البيتكوين، الفوركس، النازداك والنفط.\n"
            f"جرّب: 'حلل الذهب' أو 'ما رأيك في البيتكوين؟'\n\n"
            f"متبقي لك **{remaining + 1}** محادثات مجانية."
        )
    elif any(w in msg for w in ["شكر","ممتاز","حلو","great","thanks","thank"]):
        reply = (
            "Thanks! Happy to help 😊 Sign up now for the full Smart Analysis experience."
            if en else
            "شكراً! سعيد بمساعدتك 😊 سجّل الآن للوصول لكامل تحليلات «تحليل ذكي»."
        )
    else:
        reply = (
            f"Ask me about any trading pair!\n"
            f"Examples: 'Analyze Gold', 'Bitcoin outlook', 'What about NASDAQ?'\n\n"
            f"You have **{remaining + 1}** free chats left."
        ) if en else (
            f"اسألني عن أي زوج تداول!\n"
            f"مثال: 'حلل الذهب'، 'توصية البيتكوين'، 'ما رأيك في النازداك؟'\n\n"
            f"متبقي لك **{remaining + 1}** محادثات مجانية."
        )

    return {
        "action": "text",
        "message": reply,
        "messages_left": remaining,
    }
