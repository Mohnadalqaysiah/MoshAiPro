"""
Qaffel AI — Public Chat (Landing Page)
محادثة عامة بدون تسجيل، محدودة بـ 5 رسائل، تعرض تحليلاً مشفراً
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


@router.post("/chat")
async def public_chat(data: PublicChatIn):
    sid   = data.session_id[:64]
    count = _session_counts.get(sid, 0)

    if count >= MAX_FREE_MESSAGES:
        return {
            "action": "register_cta",
            "message": (
                "🔒 استهلكت محادثاتك المجانية الخمس.\n\n"
                "سجّل الآن للوصول الكامل لـ كفيل AI:\n"
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
    analysis_words = ["حلل","تحليل","analyze","signal","اشتري","ابيع","بيع","شراء",
                      "توصية","recommendation","entry","دخول","سعر","price"]
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
            f"أهلاً! أنا كفيل — وكيل التداول الذكي من Qaffel AI 👋\n\n"
            f"أستطيع تحليل الذهب، البيتكوين، الفوركس، النازداك والنفط.\n"
            f"جرّب: 'حلل الذهب' أو 'ما رأيك في البيتكوين؟'\n\n"
            f"متبقي لك **{remaining + 1}** محادثات مجانية."
        )
    elif any(w in msg for w in ["شكر","ممتاز","حلو","great","thanks","thank"]):
        reply = "شكراً! سعيد بمساعدتك 😊 سجّل الآن للوصول لكامل تحليلات كفيل AI."
    else:
        reply = (
            f"اسألني عن أي زوج تداول!\n"
            f"مثال: 'حلل الذهب'، 'توصية البيتكوين'، 'ما رأيك في النازداك؟'\n\n"
            f"متبقي لك **{remaining + 1}** محادثات مجانية."
        )

    return {
        "action": "text",
        "message": reply,
        "messages_left": remaining,
    }
