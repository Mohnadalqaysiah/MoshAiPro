"""
messages.py (2026-10-19) — نصوص رسائل تيليجرام بتصميم موحّد (HTML).

لماذا ملف منفصل: دوال نقية بلا telegram ولا شبكة، فتُختبر وتُعرض نماذجها دون تشغيل البوت
(telegram-bot/tests/test_messages.py). bot.py يستدعيها ويمرّر أسماء الأسواق والفريمات.

مبادئ التصميم (طلب المالك 19/10):
  - السطر الأول يقول ماذا تفعل (شراء الذهب) أو ماذا حدث (الهدف 2 تحقق) — لا زخرفة قبله.
  - R هو الرقم الرئيسي في كل النتائج (النقاط لا تُجمع بين الرموز — DECISIONS.md)، والنسبة % ثانوية.
  - المموّهة لا تكشف الاتجاه ولا الثقة ولا المستويات — السوق والفريم فقط.
  - المنتهي اشتراكه يستلم كل النتائج، الرابحة مفصّلة والخاسرة مختصرة — **لا تُخفى خسارة**.
HTML لا Markdown: أسماء مثل XAU_USD أو نص فيه * كانت تكسر Markdown فتضيع الرسالة؛ كل نص متغيّر يُهرَّب.
"""
from datetime import datetime, timedelta, timezone
from html import escape as _e
from typing import Optional

RIYADH = timezone(timedelta(hours=3))
DISCLAIMER = "<i>تحليل فني للمعلومات فقط — ليس نصيحة استثمارية.</i>"
# (2026-10-24، طلب المالك) معرّف القناة العامة بكل الرسائل الرئيسية — مع زر "📢 قناة Qaffel" بـbot.py
CHANNEL_HANDLE = "@QaffelPlatform"
CHANNEL_LINE = f"📢 قناتنا: {CHANNEL_HANDLE}"


class TeaserGate:
    """(2026-10-24) سقف منشورات القناة: ~26 إشارة/يوم تُغرق القناة فيكتمها المتابعون. مرة واحدة لكل قرار، وحد يومي،
    وفاصل أدنى بين منشورين. نقي (بلا شبكة) ليُختبر."""

    def __init__(self, daily_max: int = 6, min_gap_min: int = 60):
        self.daily_max, self.min_gap = daily_max, timedelta(minutes=min_gap_min)
        self.day, self.count, self.last, self.seen = None, 0, None, set()

    def allow(self, key, now: datetime) -> bool:
        if self.daily_max <= 0 or key in self.seen:
            return False
        if self.day != now.date():
            self.day, self.count, self.seen = now.date(), 0, set()
        if self.count >= self.daily_max or (self.last and now - self.last < self.min_gap):
            return False
        return True

    def mark(self, key, now: datetime):
        self.seen.add(key)
        self.count += 1
        self.last = now


def fmt_price(v) -> str:
    if v is None:
        return "—"
    f = float(v)
    if f > 999:
        return f"{f:,.2f}"
    return f"{f:.5f}".rstrip("0").rstrip(".")


def r_of(entry, sl, price, is_buy: bool) -> Optional[float]:
    try:
        e, s, p = float(entry), float(sl), float(price)
    except (TypeError, ValueError):
        return None
    risk = abs(e - s)
    if not risk:
        return None
    return ((p - e) if is_buy else (e - p)) / risk


def fmt_r(r: Optional[float], digits: int = 1) -> str:
    if r is None:
        return "—"
    if abs(r) < 0.05:
        return "0R"
    return f"{r:+.{digits}f}R".replace("-", "−")


def _ts(iso) -> Optional[datetime]:
    if not iso:
        return None
    if isinstance(iso, datetime):
        d = iso
    else:
        try:
            d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _ar_count(n: int, one: str, two: str, few: str, many: str) -> str:
    """عدد + تمييز بقواعد العربية: ساعة / ساعتان / 3 ساعات / 11 ساعة."""
    if n == 1:
        return one
    if n == 2:
        return two
    return f"{n} {few}" if 3 <= n % 100 <= 10 else f"{n} {many}"


def ago(iso, now: Optional[datetime] = None) -> str:
    d = _ts(iso)
    if not d:
        return ""
    mins = int(((now or datetime.now(timezone.utc)) - d).total_seconds() // 60)
    if mins < 60:
        return _ar_count(max(mins, 1), "دقيقة", "دقيقتين", "دقائق", "دقيقة")
    h = mins // 60
    if h < 24:
        hrs = _ar_count(h, "ساعة", "ساعتين", "ساعات", "ساعة")
        return hrs if mins % 60 < 10 else f"{hrs} و{_ar_count(mins % 60, 'دقيقة', 'دقيقتين', 'دقائق', 'دقيقة')}"
    return _ar_count(h // 24, "يوم", "يومين", "أيام", "يوماً")


def _deadline(iso) -> str:
    d = _ts(iso)
    if not d:
        return ""
    loc = d.astimezone(RIYADH)
    return f"⏳ أقصى مهلة <b>{loc:%H:%M}</b> ({loc:%d/%m}) بتوقيت السعودية — الإعداد قد يتغيّر قبلها"


def _side(stype: str):
    buy = stype == "BUY"
    return buy, ("🟢" if buy else "🔴"), ("شراء" if buy else "بيع")


# ─── الإشارة الجديدة (مشترك / تجربة بحصة) ────────────────────────────────────
def signal_full(s: dict, mname: str, tf_label: str, conf: float) -> str:
    buy, dot, side = _side(s.get("signal_type", "BUY"))
    entry, sl, tp1, tp2 = s.get("entry_price"), s.get("stop_loss"), s.get("take_profit_1"), s.get("take_profit_2")
    r1, r2 = r_of(entry, sl, tp1, buy), r_of(entry, sl, tp2, buy)
    mode = {"SWING": "اتجاه رئيسي", "SCALP": "صفقة سريعة"}.get(s.get("trade_type") or "")
    lines = [
        f"{dot} <b>{side} {_e(mname)}</b>  ·  <code>{_e(s.get('market', ''))}</code>",
        f"<i>إطار {_e(tf_label)}  ·  ثقة {conf:.0f}%" + (f"  ·  {mode}" if mode else "") + "</i>",
        "",
        f"▫️ الدخول      <code>{fmt_price(entry)}</code>",
        f"🛑 الوقف        <code>{fmt_price(sl)}</code>   <i>−1R</i>",
        f"🎯 الهدف 1    <code>{fmt_price(tp1)}</code>   <i>{fmt_r(r1)}</i>",
    ]
    if tp2 and float(tp2) != float(tp1 or 0):
        lines.append(f"🏁 الهدف 2    <code>{fmt_price(tp2)}</code>   <i>{fmt_r(r2)}</i>")
    lines += ["", "🛡 عند الهدف 1 انقل الوقف لنقطة الدخول لتأمين الصفقة."]
    if s.get("expires_at"):
        lines.append(_deadline(s["expires_at"]))
    if s.get("trade_type_warning"):
        lines.append(f"⚠️ {_e(str(s['trade_type_warning']))}")
    if s.get("news_context"):
        lines.append(f"📰 <i>{_e(str(s['news_context']))}</i>")
    lines += ["", DISCLAIMER, CHANNEL_LINE]
    return "\n".join(lines)


# ─── الإشارة المموّهة (بلا اتجاه ولا ثقة ولا مستويات) ─────────────────────────
def signal_masked(s: dict, mname: str, tf_label: str) -> str:
    # (2026-10-19) النص بصياغة المالك حرفياً
    return "\n".join([
        f"🔒 <b>إشارة جديدة — {_e(mname)}</b>  ·  <code>{_e(s.get('market', ''))}</code>",
        "",
        f"⏱ الإطار الزمني: {_e(tf_label)}",
        "",
        f"تصدر الآن إشارة جديدة على {_e(mname)} لمشتركي Qaffel.",
        "",
        "تفاصيل الإشارة الكاملة متاحة <b>للمشتركين</b>، وتشمل الاتجاه وسعر الدخول ووقف الخسارة والأهداف.",
        "",
        "✨ لا تفوّت الإشارة القادمة. فعّل اشتراكك واحصل على جميع التفاصيل <b>لحظة صدورها</b>.",
        "",
        CHANNEL_LINE,
    ])


# ─── النتيجة للمشترك ─────────────────────────────────────────────────────────
_HEAD = {"TP2_HIT": "🏆 الهدف 2 تحقق", "TP1_HIT": "✅ الهدف 1 تحقق",
         "BREAKEVEN": "⚖️ أُغلقت على التأمين", "SL_HIT": "🔴 ضُرب وقف الخسارة"}


def _exit_price(o: dict):
    return {"SL_HIT": o.get("sl"), "TP1_HIT": o.get("tp1"), "TP2_HIT": o.get("tp2"),
            "BREAKEVEN": o.get("entry")}.get(o.get("status")) or o.get("current_price")


def outcome_result_r(o: dict) -> Optional[float]:
    st = o.get("status")
    if st == "SL_HIT":
        return -1.0
    if st == "BREAKEVEN":
        return 0.0
    buy = o.get("signal_type") == "BUY"
    return r_of(o.get("entry"), o.get("sl"), _exit_price(o), buy)


def outcome_subscriber(o: dict, mname: str) -> str:
    st = o.get("status")
    buy, _, side = _side(o.get("signal_type", "BUY"))
    r = outcome_result_r(o)
    pct = float(o.get("pnl_pct") or 0)
    tip = {"TP2_HIT": "الهدف الكامل — صفقة ممتازة 🎯",
           "TP1_HIT": "الهدف التالي هو الهدف 2 — الوقف على الدخول يحمي الربح 🛡",
           "BREAKEVEN": "التأمين حمى رأس المال — هذا دوره 🛡",
           "SL_HIT": "الخسارة محسوبة مسبقاً (−1R) — الالتزام بالخطة هو ما يربح على المدى الطويل"}.get(st, "")
    lines = [
        f"<b>{_HEAD.get(st, st)} — {_e(mname)}</b>  ·  {side}",
        "",
        f"<b>{fmt_r(r)}</b>   <i>({pct:+.2f}%)</i>",
        f"الدخول <code>{fmt_price(o.get('entry'))}</code>  ➜  "
        f"{ {'TP1_HIT': 'الهدف 1', 'TP2_HIT': 'الهدف 2', 'SL_HIT': 'الوقف', 'BREAKEVEN': 'الدخول'}.get(st, 'الإغلاق') } "
        f"<code>{fmt_price(_exit_price(o))}</code>",
    ]
    if o.get("created_at"):
        lines.append(f"⏱ بعد {ago(o['created_at'])} من الإشارة")
    if tip:
        lines += ["", f"<i>{tip}</i>"]
    lines.append(CHANNEL_LINE)
    return "\n".join(lines)


# ─── النتيجة للمنتهي اشتراكه: الرابحة مفصّلة، الخاسرة مختصرة — كلها تصل ─────
def outcome_expired(o: dict, mname: str) -> str:
    st = o.get("status")
    _, _, side = _side(o.get("signal_type", "BUY"))
    r = outcome_result_r(o)
    mkt = _e(o.get("market", ""))
    if st in ("TP1_HIT", "TP2_HIT"):
        # (2026-10-19) صياغة المالك حرفياً
        target = "الهدف الثاني" if st == "TP2_HIT" else "الهدف الأول"
        r_txt = fmt_r(r).replace(".0R", "R")
        lines = [
            f"🏆 <b>نتيجة إشارة من Qaffel — {target} تحقق!</b>",
            "",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"🥇 <b>{_e(mname)}  ·  {mkt}  ·  {side}</b>",
            "",
            f"🎯 الدخول: <code>{fmt_price(o.get('entry'))}</code>",
            f"🛑 وقف الخسارة: <code>{fmt_price(o.get('sl'))}</code>",
            f"🏆 {target}: <code>{fmt_price(_exit_price(o))}</code>",
            "",
            f"📈 النتيجة: <b>{r_txt}</b> ({float(o.get('pnl_pct') or 0):+.2f}%)",
        ]
        if o.get("created_at"):
            lines += ["", f"⏱ وصلت هذه النتيجة بعد {ago(o['created_at'])} من صدور الإشارة للمشتركين."]
        lines += [
            "",
            "🔓 مشتركو الخطط استلموا تفاصيل الإشارة كاملة <b>لحظة صدورها</b>.",
            "",
            "✨ جدّد اشتراكك لتصلك الإشارات القادمة <b>قبل</b> تحقق نتائجها.",
            "",
            CHANNEL_LINE,
        ]
        return "\n".join(lines)
    if st == "BREAKEVEN":
        return f"⚖️ إشارة {_e(mname)}  ·  {mkt}  ·  أُغلقت على نقطة الدخول — <b>0R</b>"
    return (f"❌ إشارة {_e(mname)}  ·  {mkt}  ·  أُغلقت على وقف الخسارة — <b>−1R</b>\n\n"
            "📊 في Qaffel نعرض جميع النتائج كما هي، الرابحة والخاسرة، بكل شفافية.")


# ─── لوحة "إحصائياتي" ─────────────────────────────────────────────────────────
def _bar(pct: float, n: int = 10) -> str:
    k = max(0, min(n, round(pct / 100 * n)))
    return "▰" * k + "▱" * (n - k)


def stats_card(st: dict, market_names: Optional[dict] = None) -> str:
    mn = market_names or {}
    plan_icon = {"trial": "🔵", "weekly": "🟡", "monthly": "🟣"}.get(st.get("plan", ""), "⚪")
    total, wins, losses = st.get("total_signals", 0), st.get("wins", 0), st.get("losses", 0)
    total_r, avg_r = st.get("total_r"), st.get("avg_r")
    lines = [f"📊 <b>إحصائياتك</b>  ·  {_e(st.get('full_name') or 'مستخدم')}"]
    plan = st.get("plan_label") or ""
    if plan:
        lines.append(f"{plan_icon} {_e(plan)}" + (f"  ·  ينتهي {st['ends_at']}" if st.get("ends_at") else ""))
    lines.append("")
    if not total:
        lines += ["لا صفقات مغلقة بعد — نتائجك تظهر هنا فور إغلاق أول صفقة.", ""]
    else:
        lines += [
            f"<b>{fmt_r(total_r)}</b>  صافي النتيجة" + (f"   <i>(متوسط {fmt_r(avg_r, 2)} للصفقة)</i>" if avg_r is not None else ""),
            f"{total} صفقة مغلقة  ·  ✅ {wins}  ·  ❌ {losses}  ·  ⏳ {st.get('active_signals', 0)} نشطة",
            f"الصفقات الرابحة {st.get('win_rate', 0):.0f}%   {_bar(st.get('win_rate', 0))}",
        ]
        if st.get("best_r") is not None:
            lines.append(f"🥇 أفضل صفقة {fmt_r(st['best_r'])}   ·   💔 أسوأ {fmt_r(st.get('worst_r'))}")
        recent = st.get("recent_trades") or []
        if recent:
            lines += ["", "<b>آخر الصفقات</b>"]
            for t in recent[:5]:
                icon = "✅" if t.get("status") in ("TP1_HIT", "TP2_HIT") else "⚖️" if t.get("status") == "BREAKEVEN" else "❌"
                side = "شراء" if t.get("type") == "BUY" else "بيع"
                name = mn.get(t.get("market", ""), t.get("market", ""))
                lines.append(f"{icon} {_e(name)} {side}  <b>{fmt_r(t.get('r'))}</b>  <i>{_e(t.get('closed_at', ''))}</i>")
        lines.append("")
    wl = st.get("watchlist_filter") or []
    lines.append(f"<i>محسوبة على {len(wl)} رمز بقائمة مراقبتك</i>" if wl else "<i>محسوبة على كل الرموز منذ اشتراكك</i>")
    lines.append("<i>R = النتيجة كمضاعف للمخاطرة: +1R ربح بقدر ما خاطرت، −1R خسارة الوقف.</i>")
    lines.append(CHANNEL_LINE)
    if st.get("referral_points"):
        lines.append(f"🎁 نقاط الإحالة: {st['referral_points']}")
    return "\n".join(lines)
