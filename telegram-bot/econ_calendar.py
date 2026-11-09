"""
(2026-11-09) مواعيد تحذيرات الأخبار الاقتصادية — DECISIONS 09/11 "لماذا يحظر المستخدمون البوت".

كان economic_news_alert يفحص يوم الأسبوع وحده، فيرسل "NFP بعد ساعة" كل جمعة، و"قرار الفيدرالي" كل أربعاء، و"CPI" كل ثلاثاء،
والحقيقي شهري أو أندر: نحو 3 تحذيرات كاذبة أسبوعياً لكل المستخدمين. وساعاتها كانت ثابتة بـUTC، فتنزاح ساعة بتوقيت نيويورك الشتوي.

الآن:
- NFP: أول جمعة بالشهر، 08:30 بتوقيت نيويورك (مع التوقيت الصيفي). قاعدة الأغلب؛ يتأخر الإصدار أسبوعاً بأشهر قليلة (عطلات).
- FOMC وCPI: مواعيدهما لا تتبع قاعدة ثابتة، فلا تحذير إلا بتاريخ مكتوب بـEXTRA_EVENTS (يُملأ من التقويم الرسمي). بلا تاريخ = لا تحذير.
"""
from datetime import date, datetime, timedelta, timezone

# ("FOMC" أو "CPI"، وقت الخبر بتوقيت UTC). أمثلة الصيغة: ("FOMC", datetime(2026, 12, 9, 19, 0, tzinfo=timezone.utc))
EXTRA_EVENTS: list = []


def _nth_sunday(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def ny_utc_offset(d: date) -> int:
    """ساعات الفرق بين نيويورك وUTC: 4 صيفاً (من ثاني أحد بمارس) و5 شتاءً (من أول أحد بنوفمبر)."""
    return 4 if _nth_sunday(d.year, 3, 2) <= d < _nth_sunday(d.year, 11, 1) else 5


def first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def nfp_utc(year: int, month: int) -> datetime:
    d = first_friday(year, month)
    return datetime(d.year, d.month, d.day, 8 + ny_utc_offset(d), 30, tzinfo=timezone.utc)


def events_on(day: date) -> list:
    """[(النوع، وقت UTC)] للأخبار في هذا اليوم."""
    out = []
    nfp = nfp_utc(day.year, day.month)
    if nfp.date() == day:
        out.append(("NFP", nfp))
    out += [(k, t) for k, t in EXTRA_EVENTS if t.date() == day]
    return out


def due(now: datetime, lo_min: int = 55, hi_min: int = 65) -> list:
    """الأخبار التي يحين تحذيرها الآن (قبلها بساعة تقريباً)."""
    return [(k, t) for k, t in events_on(now.date()) if lo_min * 60 <= (t - now).total_seconds() <= hi_min * 60]
