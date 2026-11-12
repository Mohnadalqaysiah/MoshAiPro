"""
(2026-11-12) "الإعداد الموصى به" للعميل — قرار المالك "طبقه وبدي يبقى بالمنصة وفيه نصيحة مرتبه".

المصدر: diag_pref_profiles.py (614 قراراً 14/10–12/11): استقبال كل الإشارات +281R — لا فريم ولا حد ثقة أعلى منه
(1h فقط +180R، ثقة 65%+ +130R)، والثقة لا ترتّب الربح (60-64% أفضل من 65-69%). DECISIONS.md 12/11.

مصدر واحد للقيم: الموقع (/auth/preferences/recommended) والبوت (/bot/apply-recommended) يطبّقان نفس الدالة.
اتفاقية القوائم كما في البث: فارغة = الكل. لا يُطبَّق على أحد تلقائياً — فقط من يضغط الزر.
"""

RECOMMENDED = {
    "notify_watchlist": [],        # كل الأسواق (ما أوقفناه من المصدر لا يصل أحداً أصلاً)
    "notify_timeframes": [],       # كل الفريمات
    "notify_min_confidence": 0,    # بلا حد ثقة
    "notifications_enabled": True,
}


def deviations(user) -> list[str]:
    """ما يختلف به إعداد العميل عن الموصى به: watchlist / timeframes / confidence / notifications."""
    out = []
    if user.notify_watchlist:
        out.append("watchlist")
    if [t for t in (user.notify_timeframes or []) if t != "all"]:
        out.append("timeframes")
    if user.notify_min_confidence:
        out.append("confidence")
    if user.notifications_enabled is False:
        out.append("notifications")
    return out


def apply(user) -> None:
    """يضبط العميل على الموصى به (بلا commit — المستدعي يحفظ)."""
    user.notify_watchlist = list(RECOMMENDED["notify_watchlist"])
    user.notify_timeframes = list(RECOMMENDED["notify_timeframes"])
    user.notify_min_confidence = RECOMMENDED["notify_min_confidence"]
    user.notifications_enabled = RECOMMENDED["notifications_enabled"]
