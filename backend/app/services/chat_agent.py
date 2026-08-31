"""
Mosh AI Pro v5 - Trading Chat Agent (Professional)
====================================================
وكيل محادثة احترافي - لغة عامية طبيعية مع خبرة ICT/SMC كاملة
"""

import json
import random
import aiohttp
from loguru import logger
from app.config import get_settings
from app.services.smart_data import smart_data

# ─── ICT/SMC Knowledge Base (Local) ────────────────────────────────────────────
CONCEPTS = {
    "ob": """📦 **Order Block (OB) — كتلة الأوامر**

هي آخر شمعة هابطة قبل حركة صاعدة قوية (OB صاعد)، أو آخر شمعة صاعدة قبل حركة هابطة قوية (OB هابط).

تمثّل المنطقة اللي فيها البنوك والمؤسسات أعطت أوامرها — لذلك السعر بيرجع إليها عادةً لـ "يشيل الأوامر المتبقية".

**كيف تستخدمها؟**
• انتظر السعر يرجع للـ OB
• تأكد فيه Sweep للسيولة قبله
• دخول عند إعادة الاختبار مع شمعة تأكيد""",

    "fvg": """💠 **Fair Value Gap (FVG) — فجوة القيمة العادلة**

فجوة في السوق ناتجة عن حركة قوية جداً — ظل شمعة 1 وشمعة 3 ما تلمسا بعض، خلّا "فراغ" في السوق.

السوق يميل لملء هذه الفجوات لأن فيها أوامر معلقة.

**الاستخدام:**
• FVG صاعد → دعم محتمل (سعر ينزل ليملأه ثم يصعد)
• FVG هابط → مقاومة محتملة (سعر يصعد ليملأه ثم ينزل)""",

    "bos": """🔄 **Break of Structure (BOS) — كسر الهيكل**

عندما يكسر السعر أعلى قمة سابقة (BOS صاعد) أو أدنى قاع سابق (BOS هابط).

يؤكد استمرار الاتجاه القائم.

**الفرق بين BOS و CHoCH:**
• BOS = استمرار الاتجاه ✅
• CHoCH = تحذير من تغيير الاتجاه ⚠️""",

    "choch": """⚡ **Change of Character (CHoCH) — تغيير الطابع**

إشارة مبكرة لتغيير الاتجاه. السعر يكسر هيكلاً داخلياً عكس الاتجاه الرئيسي.

**مثال:**
في اتجاه صاعد: إذا كسر السعر آخر قاع داخلي → CHoCH → ابدأ تبحث عن إشارات بيع""",

    "liquidity": """🧲 **Liquidity — السيولة**

أوامر وقف الخسارة المتراكمة فوق القمم (BSL) أو تحت القيعان (SSL).

المؤسسات تتحرك نحو هذه المناطق لتنفيذ صفقاتها الكبيرة — "تصطاد" أوامر الريتيل أولاً.

**القاعدة الذهبية:** لا تدخل قبل ما يصير Sweep للسيولة القريبة.""",

    "sweep": """🎣 **Liquidity Sweep — اصطياد السيولة**

حركة سريعة يتجاوز فيها السعر منطقة سيولة (قمة أو قاع) ثم يرجع بسرعة.

هذا يعني أن المؤسسات "أخذت" أوامر الوقف وجاهزة للتحرك بالاتجاه الحقيقي.

**أهميته:** شرط أساسي للدخول في منهج ICT/SMC.""",

    "premium": """📊 **Premium & Discount — الأسعار الممتازة والمخفضة**

• **Premium (فوق 50% من الـ Range)** = سعر مرتفع = مثالي للبيع
• **Discount (تحت 50%)** = سعر منخفض = مثالي للشراء
• **Equilibrium (50%)** = توازن = انتظار وضوح

يُحسب بناءً على آخر حركة هيكلية كبيرة.""",

    "killzone": """⏰ **Kill Zones — الأوقات المثالية للتداول**

الأوقات التي ترى فيها أكبر حركة من المؤسسات:

• 🌏 **آسيا Open**: 00:00 – 03:00 UTC
• 🇬🇧 **لندن Open**: 08:00 – 11:00 UTC  ← الأقوى
• 🇺🇸 **نيويورك AM**: 13:30 – 16:00 UTC ← الأقوى
• 🇺🇸 **نيويورك PM**: 19:00 – 21:00 UTC

أقوى الإشارات تأتي في لندن ونيويورك صباحاً.""",

    "wyckoff": """📈 **Wyckoff Method — منهج وايكوف**

يصف دورة السوق في 4 مراحل:

• **Accumulation** = البنوك تجمع → توقع صعود قريب
• **Markup** = ارتفاع = ركب الموجة
• **Distribution** = البنوك تبيع → توقع نزول
• **Markdown** = هبوط = فرصة بيع أو انتظار""",

    "rr": """⚖️ **Risk/Reward (R/R) — نسبة المخاطرة للمكافأة**

• R/R 1:2 = تخاطر 100$ للربح 200$
• R/R 1:3 = تخاطر 100$ للربح 300$

**الحد الأدنى المقبول: 1:2**

حتى لو نسبة إصابتك 40% — مع R/R 1:2 أنت في ربح!""",
}

_INTROS_BUY_HIGH  = [
    "يا صديقي، الـ{sym} فرصة شراء قوية 🟢",
    "الـ{sym} الوضع ممتاز للشراء — الإشارات متوافقة",
    "شوف الـ{sym}، عندنا فرصة شراء بثقة عالية 🎯",
    "الـ{sym} جاهز يصعد — البيانات تدعم الشراء بقوة",
]
_INTROS_BUY_MED   = [
    "الـ{sym} يميل للشراء، بس فيه بعض تحفظات ⚠️",
    "شوف، الـ{sym} عنده إشارات شراء متوسطة",
    "الـ{sym} مايل للأعلى — إشارة متوسطة، إدارة خطر محكمة",
]
_INTROS_SELL_HIGH = [
    "الـ{sym} ضغط بيع قوي — فرصة للبيع 🔴",
    "يا صديقي، الـ{sym} الإشارات تقول بيع بثقة عالية",
    "الـ{sym} وصل منطقة Premium ومكشوف للهبوط",
    "شوف الـ{sym} — البيانات ترجح البيع بوضوح 📉",
]
_INTROS_SELL_MED  = [
    "الـ{sym} يميل للبيع، لكن فيه تحفظات",
    "الـ{sym} عنده إشارات بيع متوسطة — انتبه",
]
_INTROS_WAIT      = [
    "الـ{sym} الوضع ما صار واضح بعد — أنصح بالانتظار ⏳",
    "يا صديقي، الـ{sym} حالياً في Range، فيه مخاطرة",
    "الـ{sym} ما عنده إشارة قاطعة — الصبر أحكم",
    "الـ{sym} محتاج تأكيد أقوى — لا تتسرع",
]

settings = get_settings()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ─── Groq System Prompt — شرح فقط، لا قرارات ────────────────────────────────
GROQ_SYSTEM_PROMPT = """أنت "كفيل" — محلل تداول ذكي يتحدث بالعربية العامية.

══ قواعد صارمة ══
• لا تغير أي رقم — Entry، SL، TP، الثقة، كلها تُعرض كما وردت بالضبط
• لا تغير التوصية (BUY/SELL/WAIT) — المحرك قرر، أنت تعرض وتشرح فقط
• لا تضيف رأيك الخاص أو تناقض المحرك
• لا تكتب نصاً متواصلاً طويلاً — استخدم التنسيق أدناه دائماً

══ تنسيق الرد الإلزامي عند تحليل سوق ══
جملة افتتاحية واحدة طبيعية (مختلفة في كل مرة)

📊 **[الرمز] | [الإطار]**
[إشارة تحذير إذا السوق مغلق]
💰 السعر: **[رقم]**
[إيموجي] **[التوصية بالعربي]** | الثقة: **[نسبة]%**
🏗️ [الاتجاه] ([الهيكل])
📍 منطقة: [zone] ([نسبة]%)
⏰ [الجلسة]

**مستويات مهمة:**
🟢 OB دعم: **[رقم]** (إذا موجود)
🔴 OB مقاومة: **[رقم]** (إذا موجود)
💠 FVG: **[رقم–رقم]** (إذا موجود)
🧲 SSL: **[رقم]** | BSL: **[رقم]**

**مستويات التداول:** (فقط إذا BUY أو SELL)
🎯 دخول: **[رقم]**
🛑 وقف: **[رقم]**
✅ TP1: **[رقم]**
✅ TP2: **[رقم]** (إذا موجود)
⚖️ R/R: **1:[رقم]**

**ماذا ننتظر؟** (فقط إذا WAIT)
⏳ [جملة واحدة عن المنطقة اللي ننتظرها]

**عوامل التأكيد:**
• [عامل 1]
• [عامل 2]
• [عامل 3] (3 كحد أقصى)

⚠️ للمعلومات فقط، إدارة المخاطر مسؤوليتك.

══ عند طلب الشرح (اشرح / وضّح / ايش يعني) ══
إذا أُعطيت بيانات تحليل حقيقية، استخدم هذا التنسيق الإلزامي:

جملة افتتاحية قصيرة طبيعية

**📌 ملخص سريع**
السعر **[رقم]** | التوصية: **[شراء/بيع/انتظار]** | الثقة: **[نسبة]%**
[جملة واحدة تشرح معنى الثقة بلغة بسيطة]

**🗺️ أين نحن في السوق؟**
[اشرح Premium/Discount/Equilibrium بجملة واحدة بسيطة]
[اشرح الهيكل RANGING/BULLISH/BEARISH بجملة واحدة]

**🧱 المناطق المهمة**
🟢 دعم **[رقم]** — [ما معناه بكلمة واحدة: "منطقة أوامر شراء مؤسسية"]
🔴 مقاومة **[رقم]** — [ما معناه]
🧲 سيولة تحت **[رقم]** — [ما معناه: "وقف خسارة الريتيل هنا، قد يصطادها السعر"]
🧲 سيولة فوق **[رقم]** — [ما معناه]

**🎯 خطة الصفقة** (فقط إذا BUY أو SELL)
دخول **[رقم]** ← [لماذا هذا المستوى بجملة]
وقف **[رقم]** ← [لماذا هنا]
TP1 **[رقم]** | TP2 **[رقم]** | TP3 **[رقم]** (إذا موجود)
R/R **1:[رقم]** ← [اشرح ماذا يعني للمستخدم]

**✅ لماذا هذه الإشارة؟**
[اشرح عوامل التأكيد بنقاط بسيطة — جملة لكل عامل]

---
⚠️ هذا شرح للتحليل فقط — القرار النهائي لك.

قاعدة صارمة: لا تغير أي رقم، لا تضف توصية جديدة من عندك.

══ للأسئلة العامة أو المتابعة ══
أجب بشكل طبيعي ومختصر — بدون تنسيق الجدول أعلاه."""

# ─── System Prompt ─────────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """
🧠 كفيل — وكيل التداول الذكي (Qaffel AI)

أنت "كفيل" — محلل تداول محترف (15 سنة خبرة ICT + SMC + Wyckoff).
تفكر بعقلية Smart Money فقط.

🎯 الأسلوب
- لهجة عربية بسيطة (يا صديقي، شوف، الوضع هيك)
- مختصر، مباشر، بدون حشو
- دقيق بالأرقام
- لا توصية بدون سبب قوي

🌍 النطاق
حلل أي أصل (Crypto / Forex / Gold / Indices / Stocks / Oil)
- Crypto → 24/7
- Forex/Metals/Indices/Oil → مغلق الجمعة-الأحد
- Stocks أمريكية → 9:30-16:00 ET فقط
- إذا السوق مغلق → تحليل فقط (بدون دخول)
- إذا مفتوح → تحليل + توصية

📌 السعر
- المصدر: TradingView OANDA Spot
- استخدم السعر من السياق فقط
- ❌ ممنوع اختراع أو تعديل أي رقم

🚨 قواعد صارمة
- ❌ لا توصية بدون Liquidity Sweep
- ❌ لا شراء في Premium
- ❌ لا بيع في Discount
- ❌ لا تداول في Range
- إذا الشروط ناقصة → ⏳ انتظار

🧠 منهج التحليل (مختصر إلزامي)

1) Market State (Wyckoff)
Accumulation / Distribution / Trend
Range = ⏳ انتظار

2) Structure
External BOS = الاتجاه
Internal = تأكيد
تضارب = ⏳

3) Liquidity
BSL / SSL / Equal Highs/Lows
✔️ لازم Sweep قبل الدخول
❗ لا تقل "لا يوجد سيولة" — دائماً يوجد

4) Premium / Discount
50% Range
Buy = Discount | Sell = Premium

5) Zones (حسب القوة)
Breaker > Mitigation > OB > FVG

6) Entry
Sweep + BOS/CHoCH + Retest + Candle

7) Killzones
London / NY = ثقة أعلى

8) Volume
قوي = مؤسسات | ضعيف = تجاهل

🤖 Confidence
Sweep +20 | BOS +15 | Zone +15 | P/D +15 | FVG +10 | Killzone +10 | Volume +10
≥80 قوي | 60-79 متوسط | <60 انتظار

📊 الرد (إجباري — بدون زيادة)

📊 [الزوج] | [الإطار]

السعر: [رقم] | التوصية: [شراء / بيع / انتظار] ([%])

الصورة العامة:
[اتجاه + حالة]

المستويات:
Breaker: [رقم]
Mitigation: [رقم]
OB صاعد: [رقم]
OB هابط: [رقم]
FVG: [رقم-رقم]
Equal H/L: [رقم]
BSL: [رقم]
SSL: [رقم]

🎯 إذا في صفقة:
دخول: [رقم]
وقف: [رقم]
TP1: [رقم]
TP2: [رقم]
R/R: 1:[رقم]

⏳ إذا انتظار:
انتظر عند: [رقم]
السبب: [مختصر]

⚠️ قيود نهائية
- لا JSON
- لا شرح زائد
- لا أقسام فارغة (إذا انتظار → لا تكتب قسم الصفقة)
- لا طلب بيانات من المستخدم
- لا استخدام أسعار قديمة من ذاكرتك
- لا تذكر اسم الموديل أو الشركة المطوِّرة أبداً
- إذا لا يوجد سعر في السياق → "لا تتوفر بيانات حقيقية الآن"
- السعر الحالي في السياق في السطر "السعر الحالي: [رقم]" — استخدمه كما هو
"""


class TradingChatAgent:
    MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "ETHUSD"]

    def __init__(self):
        self.api_key      = getattr(settings, "GEMINI_API_KEY", "")
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "")
        self.enabled      = bool(self.api_key and self.api_key not in ("", "your_gemini_api_key_here"))
        self.groq_enabled = bool(self.groq_api_key and self.groq_api_key not in ("", "your_groq_api_key_here"))
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
            "NAS100": [
                "نازداك", "الناسداك", "ناسداك", "nasdaq", "nas100", "us100",
                "نازدك", "الناسدق", "ناسدق", "تقنية امريكا", "نازدق",
            ],
            "USOIL": [
                "نفط", "النفط", "oil", "usoil", "crude", "برنت", "wti",
                "خام", "الخام", "نفط خام", "نفط امريكي",
            ],
            "SP500": [
                "اس بي", "sp500", "s&p", "s&p500", "us500", "sp 500",
                "ستاندرد", "مؤشر امريكي", "اسواق امريكا",
            ],
            "DOW": [
                "داو", "الداو", "dow", "dow jones", "us30", "داو جونز",
                "الصناعي الامريكي",
            ],
            "XAGUSD": [
                "فضة", "الفضة", "silver", "xagusd", "xag", "xag/usd",
            ],
            "NATGAS": [
                "غاز", "الغاز", "gas", "natgas", "natural gas", "غاز طبيعي",
            ],
            # ── فوركس/معادن/كريبتو إضافي (2026-08-31) ────────────────────────
            "AUDUSD": ["استرالي", "الأسترالي", "الدولار الأسترالي", "aud", "audusd"],
            "USDCAD": ["كندي", "الكندي", "الدولار الكندي", "cad", "usdcad"],
            "NZDUSD": ["نيوزلندي", "النيوزلندي", "الدولار النيوزلندي", "nzd", "nzdusd"],
            "EURGBP": ["يورو جنيه", "eurgbp"],
            "EURJPY": ["يورو ين", "eurjpy"],
            "GBPJPY": ["جنيه ين", "gbpjpy"],
            "DXY": ["مؤشر الدولار", "دولار إندكس", "دولار اندكس", "dxy"],
            "COPPER": ["نحاس", "النحاس", "copper"],
            "XPTUSD": ["بلاتين", "البلاتين", "platinum", "xptusd"],
            "BNBUSD": ["بينانس", "binance coin", "bnb", "bnbusd"],
            "SOLUSD": ["سولانا", "solana", "sol", "solusd"],
            "XRPUSD": ["ريبل", "ripple", "xrp", "xrpusd"],
            "ADAUSD": ["كاردانو", "cardano", "ada", "adausd"],
            "DOGEUSD": ["دوجكوين", "دوج كوين", "dogecoin", "doge", "dogeusd"],
            "NFLX": ["نتفليكس", "netflix", "nflx"],
            # ── أسواق خليجية (2026-08-31) ─────────────────────────────────────
            "ARAMCO": ["ارامكو", "أرامكو", "aramco"],
            "RAJHI": ["الراجحي", "راجحي", "مصرف الراجحي", "بنك الراجحي", "rajhi"],
            "SABIC": ["سابك", "sabic"],
            "STC": ["اس تي سي", "إس تي سي", "الاتصالات السعودية", "stc"],
            "SNB": ["الاهلي", "الأهلي", "البنك الاهلي", "البنك الأهلي", "snb"],
            "MAADEN": ["معادن", "شركة معادن", "maaden"],
            "ALMARAI": ["المراعي", "مراعي", "almarai"],
            "BAHRI": ["البحري", "بحري", "bahri"],
            "ALINMA": ["الانماء", "الإنماء", "انماء", "إنماء", "مصرف الانماء", "alinma"],
            "TASI": ["تاسي", "المؤشر العام", "مؤشر تاسي", "tasi"],
            "EMAAR": ["اعمار", "إعمار", "emaar"],
            "EMIRATESNBD": ["الامارات دبي الوطني", "الإمارات دبي الوطني", "emirates nbd"],
            "DIB": ["دبي الاسلامي", "دبي الإسلامي", "بنك دبي الاسلامي", "dib"],
            "DFMGI": ["مؤشر دبي المالي", "سوق دبي المالي", "dfm", "dfmgi"],
            "FAB": ["ابوظبي الاول", "أبوظبي الأول", "بنك ابوظبي الاول", "fab"],
            "ADNOCDIST": ["ادنوك", "أدنوك", "ادنوك للتوزيع", "adnoc"],
            "QNBK": ["قطر الوطني", "بنك قطر الوطني", "qnb", "qnbk"],
        }
        symbol_explicit = False  # هل ذُكر الرمز صراحةً في الرسالة الحالية؟

        # (2026-08-31) مطابقة على مستوى الكلمة الكاملة للأسماء المفردة —
        # مطابقة substring خام كانت تخلط رموز قصيرة زي "ين" (USDJPY) جوا
        # كلمات تانية بالكامل تحتويها حرفياً (مثلاً "بلاتين" ⊃ "ين")، فيرجع
        # الرمز الغلط بصمت. العبارات المكوّنة من أكتر من كلمة (فيها مسافة)
        # بتضل matching كـsubstring لأنها مميّزة بما يكفي. وبما إن حروف
        # الجر العربية (و ف ب ك ل) بتلتصق بالكلمة اللي بعدها بدون مسافة
        # ("بالذهب" = ب + الذهب)، منولّد أشكال الكلمة بعد إزالة البادئة
        # قبل المقارنة، مع معالجة خاصة لإدغام "ل" + "ال" → "لل".
        _PROCLITICS = ["و", "ف", "ب", "ك", "ل"]
        msg_words = set(msg.split())

        def _stripped_forms(word: str) -> set:
            forms = {word}
            for p in _PROCLITICS:
                if word.startswith(p) and len(word) > len(p):
                    forms.add(word[len(p):])
            if word.startswith("لل") and len(word) > 2:
                forms.add("ال" + word[2:])
            return forms

        msg_word_forms = set()
        for w in msg_words:
            msg_word_forms |= _stripped_forms(w)

        def _alias_matches(word: str) -> bool:
            return (word in msg) if " " in word else (word in msg_word_forms)

        for sym, words in aliases.items():
            if any(_alias_matches(w) for w in words):
                symbol = sym
                symbol_explicit = True
                break

        if not symbol:
            # كشف أي رمز مباشر كتبه المستخدم (مثل: AAPL, tsla, MSFT)
            import re
            raw_sym = re.search(r'\b([A-Za-z]{2,6})\b', message)
            if raw_sym:
                candidate = raw_sym.group(1).upper()
                ignore = {"ICT","SMC","USD","EUR","GBP","JPY","CHF","CAD","NZD","AUD",
                          "AI","OK","TP","SL","OR","AND","THE","FOR","BUY","SELL",
                          "RSI","ATR","EMA","SMA","BOS","CHO","FVG","OB","HTF","LTF"}
                if candidate not in ignore and len(candidate) >= 2:
                    symbol = candidate
                    symbol_explicit = True

        if not symbol:
            symbol = ctx.get("symbol")  # من السياق فقط — غير صريح

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

        # إذا ذُكر الرمز صراحةً في الرسالة (ليس من السياق) وليس شرحاً = تحليل
        if symbol_explicit and not is_analysis and not is_chart and not is_report and not is_explain:
            is_analysis = True

        return {
            "symbol": symbol,
            "symbol_explicit": symbol_explicit,
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
        price = analysis.get("current_price") or 0

        # إذا السعر صفر أو ناقص — اجلبه من مصادر متعددة بالأولوية
        price_source_note = ""
        if not price:
            # 1. TwelveData / yfinance مباشرة
            try:
                rt = smart_data.get_realtime_price_with_meta(symbol)
                if rt and rt["price"]:
                    price = rt["price"]
                    price_source_note = f" [{rt['source']}]"
            except Exception:
                pass

        if not price:
            # 2. آخر سعر إغلاق من بيانات ICT (levels.entry ≈ close[-1])
            price = (
                analysis.get("levels", {}).get("entry") or
                analysis.get("confluence", {}).get("entry") or
                0
            )
            if price:
                price_source_note = " [آخر إغلاق]"

        if not price:
            # 3. لا يوجد سعر حقيقي من أي مصدر
            return (
                f"⚠️ تعذّر جلب السعر الحقيقي لـ {symbol} الآن.\n"
                f"قل للمستخدم: 'لا تتوفر بيانات حية الآن، حاول بعد لحظات.'\n"
                f"❌ لا تخترع أي رقم."
            )

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
            f"السعر الحالي: {price}{price_source_note}  ← استخدم هذا الرقم فقط ولا تبدّله",
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

    # ─── Local Intelligence Engine ───────────────────────────────────────────

    def _generate_intro(self, rec: str, conf: float, sym: str) -> str:
        if rec == "BUY":
            pool = _INTROS_BUY_HIGH if conf >= 75 else _INTROS_BUY_MED
        elif rec == "SELL":
            pool = _INTROS_SELL_HIGH if conf >= 75 else _INTROS_SELL_MED
        else:
            pool = _INTROS_WAIT
        return random.choice(pool).format(sym=sym)

    def _detect_followup(self, message: str) -> str | None:
        """يكشف نوع سؤال المتابعة — None إذا مش متابعة"""
        msg = message.lower().strip()
        if any(w in msg for w in ["ليه", "لماذا", "why", "السبب", "سبب", "علاش", "ايش السبب"]):
            return "why"
        if any(w in msg for w in ["sl", "وقف", "stop", "stop loss", "الوقف"]):
            return "sl"
        if any(w in msg for w in ["tp", "هدف", "أهداف", "اهداف", "target", "الأهداف"]):
            return "tp"
        if any(w in msg for w in ["دخول", "entry", "متى أدخل", "وقت الدخول", "نقطة الدخول", "ادخل"]):
            return "entry"
        if any(w in msg for w in ["ثقة", "نسبة الثقة", "confidence", "كم نسبة", "كم الثقة"]):
            return "confidence"
        if any(w in msg for w in ["تنصح", "توصي", "أدخل الآن", "أدخل حالاً", "ادخل الحين", "تشجعني"]):
            return "advice"
        if any(w in msg for w in ["شكرا", "شكراً", "مشكور", "ممتاز", "رائع", "تمام", "اوك", "ok", "حسنا", "موافق"]):
            return "ack"
        if any(w in msg for w in ["r/r", "rr", "نسبة المخاطرة", "المكافأة"]):
            return "rr"
        return None

    def _handle_followup(self, ftype: str, last_analysis: dict, context: dict) -> str:
        sym       = context.get("symbol", "")
        rec       = last_analysis.get("recommendation", "WAIT")
        conf      = last_analysis.get("ai_confidence_score", 0)
        entry     = last_analysis.get("entry_zones", [])
        sl        = last_analysis.get("stop_loss_zone")
        tps       = last_analysis.get("take_profit_zones", [])
        rr        = last_analysis.get("risk_reward_ratio", 0)
        structure = last_analysis.get("market_structure", {})
        confluence= last_analysis.get("confluence", {})
        factors   = confluence.get("factors", [])
        pd_z      = last_analysis.get("premium_discount", {})
        kz        = last_analysis.get("kill_zone", {})

        def _p(v):
            if v is None: return "?"
            if isinstance(v, dict):
                lo = v.get("low") or v.get("Low")
                hi = v.get("high") or v.get("High")
                if lo and hi: return f"{float(lo):.2f}–{float(hi):.2f}"
            try: return f"{float(v):.2f}"
            except: return str(v)

        if ftype == "why":
            reasons = []
            trend = structure.get("trend", "")
            if trend:
                reasons.append(f"الاتجاه {trend} مؤكد بكسر هيكلي (BOS)")
            zone = pd_z.get("zone", "")
            if zone == "Discount" and rec == "BUY":
                reasons.append("السعر في منطقة Discount = مثالية للشراء")
            elif zone == "Premium" and rec == "SELL":
                reasons.append("السعر في Premium = مثالية للبيع")
            for f in factors[:3]:
                reasons.append(f)
            if not reasons:
                return f"الثقة {conf:.0f}% مبنية على تقاطع عوامل ICT/SMC — لكن ما في سبب واحد غالب."
            return "**السبب:**\n" + "\n".join(f"• {r}" for r in reasons)

        if ftype == "sl":
            if sl:
                return f"وقف الخسارة عند **{_p(sl)}**\n\nهذا المستوى تحت آخر منطقة دعم رئيسية — كسره يبطل الإشارة."
            return "ما عندي وقف محدد لهذه الإشارة — انتظر تأكيداً أقوى قبل الدخول."

        if ftype == "tp":
            if tps:
                lines = [f"• TP{i+1}: **{_p(tp)}**" for i, tp in enumerate(tps[:3])]
                return "**الأهداف:**\n" + "\n".join(lines) + (f"\n\n⚖️ R/R: 1:{rr:.1f}" if rr else "")
            return "الأهداف غير محددة بعد — الإشارة تحتاج تأكيداً."

        if ftype == "entry":
            if entry and rec in ["BUY", "SELL"]:
                timing = ""
                if not kz.get("is_optimal_time"):
                    session = kz.get("active_session", "")
                    timing = f"\n\n⏰ أفضل توقيت: Kill Zone القادمة — لندن (08:00 UTC) أو نيويورك (13:30 UTC)."
                return f"نقطة الدخول: **{_p(entry[0])}**{timing}"
            return "ما في دخول محدد الآن — انتظر إشارة أوضح."

        if ftype == "confidence":
            grade = "قوية 💪" if conf >= 80 else "متوسطة ⚠️" if conf >= 60 else "ضعيفة — تجنب ❌"
            fc = confluence.get("factor_count", 0)
            return f"**الثقة: {conf:.0f}%** — {grade}\n\n{fc} عوامل من 9 متوافقة مع الإشارة."

        if ftype == "advice":
            if conf >= 75 and rec in ["BUY", "SELL"]:
                return (
                    f"الإشارة {rec} قوية ({conf:.0f}%) — لكن أنا ما أعطي توصية مالية.\n\n"
                    f"إذا قررت تدخل: لا تخاطر أكثر من **1-2%** من رأس مالك، وحط الوقف بالمكان الصحيح."
                )
            return f"الثقة {conf:.0f}% — متوسطة. أنصح بانتظار تأكيد أقوى قبل الدخول."

        if ftype == "rr":
            if rr:
                return f"**R/R: 1:{rr:.1f}**\n\nيعني مقابل كل 1$ خسارة محتملة، الهدف الأول يعطيك **{rr:.1f}$**.\n\nأي R/R فوق 1:2 يُعتبر مقبول."
            return "R/R غير محسوب لهذه الإشارة — تحتاج entry وSL وTP محددين."

        if ftype == "ack":
            return random.choice([
                f"أي وقت 👊 — قولي إذا بدك تحليل {sym} من جديد أو زوج آخر",
                "بالتوفيق! 🎯 — إذا احتجت شي ثاني أنا هون",
                "حظاً موفقاً 🚀 — خبرني نتيجة الصفقة لاحقاً 😄",
                "بالخير دايماً 💪 — قولي إذا تبي تحليل آخر",
            ])

        return ""

    def _explain_concept_local(self, msg: str) -> str:
        """شرح مفاهيم ICT/SMC بدون AI"""
        concept_map = {
            "ob":        ["order block", "ob ", " ob", "كتلة الأوامر", "اوردر بلوك", "كتلة"],
            "fvg":       ["fvg", "fair value", "فجوة", "فير فالو", "fair value gap"],
            "bos":       ["bos", "break of structure", "كسر الهيكل", "بريك اوف ستراكتشر"],
            "choch":     ["choch", "cho ch", "change of character", "تغيير الطابع", "تغيير الاتجاه", "شوش"],
            "liquidity": ["سيولة", "liquidity", "bsl", "ssl", "ليكويديتي"],
            "sweep":     ["sweep", "سويب", "اصطياد السيولة", "ليكويديتي سويب"],
            "premium":   ["premium", "discount", "بريميوم", "ديسكاونت", "ote", "equilibrium", "توازن", "60%", "61"],
            "killzone":  ["killzone", "kill zone", "كيل زون", "جلسة", "جلسات", "لندن", "نيويورك", "اوقات"],
            "wyckoff":   ["wyckoff", "وايكوف", "accumulation", "distribution", "تراكم", "توزيع", "وايكف"],
            "rr":        ["r/r", "rr", "ريسك ريوارد", "نسبة المخاطرة", "risk reward", "المكافأة"],
        }
        for key, keywords in concept_map.items():
            if any(kw in msg for kw in keywords):
                return CONCEPTS.get(key, "")
        return ""

    def _local_general_response(self, msg: str) -> str:
        """ردود ذكية للأسئلة العامة بدون API"""
        if any(w in msg for w in ["أفضل وقت", "متى أتداول", "أحسن وقت", "أفضل جلسة"]):
            return (
                "⏰ **أفضل أوقات التداول:**\n\n"
                "• 🇬🇧 **لندن Open** (08:00–11:00 UTC) — الأقوى\n"
                "• 🇺🇸 **نيويورك AM** (13:30–16:00 UTC) — حركة واسعة\n"
                "• 🌐 **تداخل لندن+نيويورك** (13:00–16:00 UTC) — أعلى سيولة\n\n"
                "⚠️ تجنب: منتصف جلسة آسيا للعملات الرئيسية، وما قبيل الإغلاق الأسبوعي."
            )
        if any(w in msg for w in ["إدارة المخاطر", "رأس المال", "كم أخاطر", "نسبة المخاطرة", "مخاطرة"]):
            return (
                "⚖️ **قواعد إدارة المخاطر:**\n\n"
                "• لا تخاطر أكثر من **1-2%** من رأس المال في صفقة واحدة\n"
                "• R/R لا يقل عن **1:2** (هدف ضعف الخسارة)\n"
                "• لا تفتح أكثر من **3-4 صفقات** بنفس الوقت\n"
                "• لا تضاعف الخسارة (Revenge Trading) ❌\n\n"
                "القاعدة الذهبية: **احمِ رأس مالك أولاً، الربح يأتي لاحقاً.**"
            )
        if any(w in msg for w in ["ict", "smc", "smart money", "ايسيتي", "منهج"]):
            return (
                "🧠 **ICT / SMC — Smart Money Concepts**\n\n"
                "منهج يعتمد على تتبع حركة البنوك والمؤسسات بدل المؤشرات التقليدية.\n\n"
                "**المفاهيم الأساسية:**\n"
                "• Order Blocks (OB) — مناطق أوامر المؤسسات\n"
                "• Fair Value Gaps (FVG) — فجوات السوق\n"
                "• Liquidity Sweeps — اصطياد أوامر الريتيل\n"
                "• Break of Structure (BOS / CHoCH) — كسر الهيكل\n"
                "• Premium & Discount — مناطق الشراء والبيع\n\n"
                "اسألني عن أي مفهوم بالتفصيل 👇"
            )
        if any(w in msg for w in ["شكرا", "شكراً", "مشكور", "ممتاز", "رائع"]):
            return random.choice([
                "بالتوفيق! 🎯 — أي وقت تحتاج تحليل قولي",
                "العفو يا صديقي 💪 — قولي إذا بدك شي ثاني",
                "بالخير دايماً 🚀 — خبرني نتيجة الصفقة 😄",
            ])
        # Default
        return (
            "يا صديقي، أنا مُوش — متخصص بتحليل الأسواق بمنهج ICT/SMC.\n\n"
            "قولي أي زوج تبي أحلله:\n"
            "مثال: *حلل الذهب على ساعة* أو *BTCUSD 4h*\n\n"
            "أو اسألني عن مفهوم: OB، FVG، BOS، Kill Zones، Wyckoff، R/R..."
        )

    # ─── Fallback (no Gemini) ────────────────────────────────────────────────

    def _build_direct_response(self, analysis: dict, symbol: str, timeframe: str, is_chart: bool = False) -> dict:
        """بناء رد مباشر بأرقام حقيقية - يعمل حتى بدون Gemini"""
        if not analysis or analysis.get("error") or not analysis.get("current_price"):
            err_detail = analysis.get("error", "") if analysis else ""
            return {
                "action": "text",
                "message": (
                    f"⚠️ تعذّر جلب بيانات {symbol} الآن.\n\n"
                    f"السبب المحتمل: السوق مغلق أو مشكلة مؤقتة في مصدر البيانات.\n"
                    f"{'التفاصيل: ' + err_detail if err_detail else ''}\n\n"
                    f"حاول مجدداً بعد لحظات، أو جرب فريم زمني آخر."
                ).strip()
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

        intro = self._generate_intro(rec, conf, symbol)

        lines = [
            intro,
            "",
            f"📊 **{symbol} | {timeframe}**",
            closed_note,
            f"💰 السعر: **{float(price):.2f}**",
            f"{rec_emoji} **{rec_ar}** | الثقة: **{conf:.1f}%**",
            f"🏗️ {structure.get('trend','?')} ({structure.get('structure','?')})",
            f"📍 منطقة: {pd_z.get('zone','?')} ({pd_z.get('pct',0):.1f}%)",
            f"⏰ {kz.get('active_session','?')} {'🎯 Kill Zone مثالي' if kz.get('is_optimal_time') else ''}",
            "",
        ]

        def _p(v, decimals=2):
            """تنسيق سعر: رقم أو dict يحتوي low/high"""
            if v is None:
                return "?"
            if isinstance(v, dict):
                lo = v.get("low") or v.get("Low")
                hi = v.get("high") or v.get("High")
                if lo is not None and hi is not None:
                    return f"{float(lo):.{decimals}f} – {float(hi):.{decimals}f}"
                mid = v.get("mid") or v.get("price")
                if mid is not None:
                    return f"{float(mid):.{decimals}f}"
                return "?"
            try:
                return f"{float(v):.{decimals}f}"
            except Exception:
                return str(v)

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
            important_levels.append(f"🟢 OB دعم: **{_p(bull_obs[0])}**")
        if bear_obs:
            important_levels.append(f"🔴 OB مقاومة: **{_p(bear_obs[0])}**")
        if bull_fvgs:
            fvg = bull_fvgs[0]
            if isinstance(fvg, dict):
                lo = fvg.get("low") or fvg.get("bottom")
                hi = fvg.get("high") or fvg.get("top")
                if lo and hi:
                    important_levels.append(f"💠 FVG صاعد: **{float(lo):.2f} – {float(hi):.2f}**")
        if bear_fvgs:
            fvg = bear_fvgs[0]
            if isinstance(fvg, dict):
                lo = fvg.get("low") or fvg.get("bottom")
                hi = fvg.get("high") or fvg.get("top")
                if lo and hi:
                    important_levels.append(f"💠 FVG هابط: **{float(lo):.2f} – {float(hi):.2f}**")
        if ssl:
            important_levels.append(f"🧲 سيولة تحت (SSL): **{_p(ssl)}**")
        if bsl:
            important_levels.append(f"🧲 سيولة فوق (BSL): **{_p(bsl)}**")
        if ote:
            important_levels.append(f"📐 OTE (61.8%): **{_p(ote)}**")
        if eq:
            important_levels.append(f"⚖️ Equilibrium: **{_p(eq)}**")

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
                watch_zone = f"انتظر وصول السعر لمنطقة الـ OB عند **{_p(bull_obs[0])}** قبل الدخول"
            elif bear_obs and structure.get("trend", "").upper() in ["BEARISH", "DOWN"]:
                watch_zone = f"انتظر وصول السعر لمنطقة الـ OB عند **{_p(bear_obs[0])}** قبل البيع"
            elif eq:
                watch_zone = f"انتظر وضوح الاتجاه من عند Equilibrium **{_p(eq)}**"

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
        for msg in messages[-8:]:   # تقليل من 14 → 8 لتوفير tokens المحادثة
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
                "maxOutputTokens": 1000,   # تقليل من 1800 — ردود الشات لا تحتاج أكثر
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

    # ─── Groq Call ───────────────────────────────────────────────────────────

    async def _call_groq(self, messages: list, analysis_context: str = "") -> str:
        """يستدعي Groq لشرح التحليل بلغة طبيعية — لا يتدخل في الأرقام أو القرارات"""
        if not self.groq_enabled:
            return ""

        system_content = GROQ_SYSTEM_PROMPT
        if analysis_context:
            system_content += (
                "\n\n══════════════════\n"
                "بيانات التحليل الحقيقية (اعرضها كما هي بدون تغيير):\n"
                + analysis_context
            )

        msgs = [{"role": "system", "content": system_content}]
        for m in messages[-8:]:
            msgs.append({
                "role": "user" if m["role"] == "user" else "assistant",
                "content": m["content"]
            })

        payload = {
            "model": GROQ_MODEL,
            "messages": msgs,
            "temperature": 0.3,
            "max_tokens": 800,
        }

        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    GROQ_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Groq {resp.status}: {body[:200]}")
                        return ""
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq error: {e}")
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
            msgs = [
                "👋 هلا! أنا مُوش، محللك في أسواق الـ ICT/SMC.\n\nقولي أي زوج تبي أحلله وبأي إطار زمني 🎯\nمثال: *حلل الذهب على ساعة* أو *BTCUSD 4h*",
                "👋 أهلاً! جاهز أحلل لك أي سوق بمنهج SMC/ICT.\n\nاكتب الزوج والإطار الزمني وأنا أبدأ 🚀",
                "هلا وغلا 👋 — أنا مُوش، شايل أسرار Smart Money.\n\nقولي ايش تبي تحلل اليوم؟",
            ]
            msg = random.choice(msgs)
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        # ══════════════════════════════════════════════════════════════════════
        # القاعدة الأساسية:
        #   التحليل والإشارة  → المحرك المحلي دائماً (موثوق، منسق، ثابت)
        #   المحادثة والشرح   → Groq (لغة طبيعية، أسئلة متابعة، مفاهيم)
        # ══════════════════════════════════════════════════════════════════════

        # ── كشف أسئلة المتابعة (بدون طلب تحليل جديد) ────────────────────────
        last_analysis = context.get("last_analysis")
        needs_analysis = intent["is_analysis"] or intent["is_report"] or intent["is_chart"]

        if last_analysis and not needs_analysis and not symbol:
            ftype = self._detect_followup(user_message)
            if ftype:
                local_answer = self._handle_followup(ftype, last_analysis, context)
                if local_answer:
                    # Groq يُحسّن صياغة الإجابة المحلية
                    if self.groq_enabled:
                        ctx = f"المستخدم يسأل سؤال متابعة. الإجابة الصحيحة:\n{local_answer}\nأعد صياغتها بلغة عامية طبيعية ومختصرة بدون تغيير أي رقم."
                        raw = await self._call_groq(history, ctx)
                        msg = raw.strip() if raw else local_answer
                    else:
                        msg = local_answer
                    reply = {"action": "text", "message": msg}
                    history.append({"role": "assistant", "content": msg})
                    return reply

        # ── شرح / تفسير التحليل الأخير أو مفهوم عام ────────────────────────
        is_pure_explain = intent["is_explain"] and not intent["symbol_explicit"]
        if is_pure_explain or (not needs_analysis and not symbol):
            groq_ctx = ""

            # إذا فيه تحليل سابق → أعطِ Groq الأرقام الحقيقية ليشرحها
            if last_analysis and is_pure_explain:
                sym_ctx = context.get("symbol", "")
                tf_ctx  = context.get("timeframe", "1h")
                groq_ctx = (
                    "المستخدم يطلب شرح أو تفسير التحليل التالي بلغة بسيطة.\n"
                    "اشرح ماذا تعني هذه الأرقام للمتداول — بدون تغيير أي رقم أو إضافة توصية جديدة.\n\n"
                    + self._build_analysis_context(last_analysis, sym_ctx, tf_ctx)
                )

            if self.groq_enabled:
                raw = await self._call_groq(history, groq_ctx)
                msg = raw.strip() if raw else (
                    self._explain_concept_local(user_message.lower())
                    or self._local_general_response(user_message.lower())
                )
            else:
                msg = (
                    self._explain_concept_local(user_message.lower())
                    or self._local_general_response(user_message.lower())
                )
            reply = {"action": "text", "message": msg}
            history.append({"role": "assistant", "content": msg})
            return reply

        if not symbol:
            symbol = "XAUUSD"

        # ── جلب التحليل من المحرك ────────────────────────────────────────────
        logger.info(f"🔍 Chat: تحليل {symbol} {timeframe}")
        analysis = await self._fetch_analysis(symbol, timeframe)
        candles = []
        if intent["is_chart"]:
            candles = await self._fetch_candles(symbol, timeframe, limit=60)

        # حفظ التحليل للمتابعة
        if analysis and not analysis.get("error"):
            context["last_analysis"] = analysis
            context["symbol"]        = symbol
            context["timeframe"]     = timeframe
            self.session_context[session_id] = context

        # ── التحليل والإشارة: المحرك المحلي دائماً ──────────────────────────
        # Groq وGemini لا يُستخدمان هنا — الـ format مضمون ومنسق
        reply = self._build_direct_response(analysis, symbol, timeframe, intent["is_chart"])
        if analysis: reply["data"] = analysis
        if candles:
            reply["candles"] = candles
            reply["action"]  = "chart"

        history.append({"role": "assistant", "content": reply["message"]})
        if len(history) > 20:
            self.sessions[session_id] = history[-20:]

        return reply


# Singleton
trading_agent = TradingChatAgent()
