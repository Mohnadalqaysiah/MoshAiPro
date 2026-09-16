"""
quality_report.py — تقرير جودة القرارات (قراءة محضة)
=======================================================
يجيب سؤالاً مختلفاً عن /admin/diagnostic. ذاك يفحص الـpipeline الحيّ
("لماذا لا تُولَّد إشارات الآن؟"). هذا يفحص السجل التاريخي:
"هل ما نقيسه صحيح، وأي شرط يستحق التشديد أو التخفيف؟"

مبادئ تحكم هذا الملف، كلها مستخلَصة من أخطاء وقعت فعلاً لا من اعتبارات
نظرية — وثلاثة منها اكتُشفت بأول تشغيل حقيقي للتقرير نفسه (16/09):

 1) القرار الفريد لا الصف. نفس القرار يُحفظ صفاً لكل مستخدم استلمه،
    فالعدّ الخام يضخّم كل شيء بمعامل عدد المستخدمين. المرجع الموحّد
    هو decision_grouping.verified_unique_decisions.

 2) الحكم بـR لا بالنقاط. النقاط ليست عملة موحّدة — راجع _r_multiple.

 3) لا اقتراح بلا حارس تضليل: عينة كافية، وتركّز رموز منخفض، وتداخل
    الفرضيات مُعلن.

لا شبكة، لا كتابة، لا مسّ للمحرك — كله من قاعدة البيانات.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

WIN    = {"TP1_HIT", "TP2_HIT"}
LOSS   = {"SL_HIT"}
CLOSED = WIN | LOSS

# عتبات الحارس — محافِظة عمداً. الخطأ باتجاه "لا اقتراح" يُصلحه جمع
# بيانات أكثر؛ والخطأ باتجاه اقتراح مضلِّل يُنفَّذ على الاستراتيجية ولا
# يُكتشف إلا بعد أسابيع من الضرر.
MIN_N_SUGGEST  = 10     # أقل عينة يجوز بناء اقتراح عليها
MIN_N_SHOW     = 3      # أقل عينة تُقرأ أصلاً
MAX_SYM_SHARE  = 0.60   # نصيب رمز واحد يتجاوزه ⇒ الحكم على الرمز لا الرافعة
MAX_TOP2_SHARE = 0.75   # ونصيب رمزين — الثغرة التي كان hhi يُحسب لها ولا يُستخدم
EXP_MARGIN     = 0.25   # أقل انحراف بـR عن خط الأساس يستحق فرضية


def _utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


# ── الشرائح ────────────────────────────────────────────────────────────
def _bucket(value: Optional[float], edges: list, none_label: str = "غير مسجّل") -> str:
    if value is None:
        return none_label
    for edge, label in edges:
        if value < edge:
            return label
    return edges[-1][1]


CONF_EDGES = [(55, "< 55%"), (65, "55–65%"), (75, "65–75%"), (85, "75–85%"), (10 ** 9, "85%+")]
RR_EDGES   = [(1.5, "< 1.5"), (2.0, "1.5–2.0"), (2.5, "2.0–2.5"), (3.0, "2.5–3.0"), (10 ** 9, "3.0+")]
SL_EDGES   = [(0.15, "< 0.15%"), (0.30, "0.15–0.30%"), (0.50, "0.30–0.50%"),
              (1.00, "0.50–1.00%"), (10 ** 9, "1.00%+")]
DUR_EDGES  = [(5, "< 5 د"), (15, "5–15 د"), (60, "15–60 د"), (240, "1–4 س"), (10 ** 9, "> 4 س")]


def _session(hour_utc: Optional[int]) -> str:
    """جلسات تقريبية بتوقيت UTC — الفائدة منها مقارنة نسبية لا توقيت دقيق."""
    if hour_utc is None:
        return "غير مسجّل"
    if hour_utc < 7:
        return "آسيا (00–07)"
    if hour_utc < 12:
        return "لندن (07–12)"
    if hour_utc < 16:
        return "تداخل لندن/نيويورك (12–16)"
    if hour_utc < 21:
        return "نيويورك (16–21)"
    return "متأخرة (21–24)"


# ── مضاعف R: المقياس الوحيد القابل للجمع عبر الرموز ────────────────────
# (2026-09-16) اكتُشف بأول تشغيل حقيقي أن النقاط ليست عملة موحّدة:
# _calc_points يعطي مضاعفاً مختلفاً لكل فئة، فحركة 1% تساوي ~360 نقطة
# على الذهب، ~200 على ناسداك، ~100 على الكريبتو، ~1.5 على سهم أمريكي،
# ~0.3 على الغاز — فارق يبلغ 1200 ضعفاً. فأي مجموع نقاط عابر للرموز
# متوسط مرجّح بأوزان اعتباطية لا علاقة لها بجودة القرار، وضبط
# الاستراتيجية عليه يضبطها على المضاعف لا على الأداء. ولا يكفي تنبيه
# القارئ: كان لا بد من مقياس بديل يُحكم به فعلاً.
# مضاعف R (العائد ÷ المخاطرة) لا يعتمد على سعر الأصل إطلاقاً — الوقف
# = −1R لأي رمز كان. ومتوسطه (التوقّع) هو الرقم الذي يُضبط عليه أي نظام
# تداول: موجب ⇒ رابح على المدى، سالب ⇒ خاسر مهما بدت النقاط.
# النقاط تبقى معروضة لأنها لغة التقارير المعتادة، لكن الحكم يُبنى على R.
def _r_multiple(entry, sl, tp1, tp2, status) -> Optional[float]:
    try:
        entry, sl = float(entry), float(sl)
        risk = abs(entry - sl)
        if risk <= 0:
            return None
        if status == "SL_HIT":
            return -1.0
        if status == "TP2_HIT" and tp2 is not None:
            return round(abs(float(tp2) - entry) / risk, 3)
        if status == "TP1_HIT" and tp1 is not None:
            return round(abs(float(tp1) - entry) / risk, 3)
    except (TypeError, ValueError):
        return None
    return None


# ── نواة التجميع ───────────────────────────────────────────────────────
def _summarize(rows: list) -> dict:
    """ملخّص مجموعة قرارات: عدد، ربح/خسارة، R، نقاط، وتركّز الرموز."""
    n      = len(rows)
    wins   = sum(1 for r in rows if r["status"] in WIN)
    losses = sum(1 for r in rows if r["status"] in LOSS)
    pts    = sum(float(r["points"] or 0) for r in rows)

    rs      = [r["r"] for r in rows if r.get("r") is not None]
    r_total = sum(rs)

    by_sym = defaultdict(int)
    for r in rows:
        by_sym[r["market"]] += 1
    ranked = sorted(by_sym.items(), key=lambda kv: -kv[1])
    top_sym, top_cnt = (ranked[0] if ranked else ("—", 0))
    top2_cnt = sum(c for _, c in ranked[:2])
    # مؤشر هيرفندال: 1.0 = رمز واحد، وكلما قلّ زاد التنوّع
    hhi = sum((c / n) ** 2 for c in by_sym.values()) if n else 0.0

    decided = wins + losses
    return {
        "n":          n,
        "wins":       wins,
        "losses":     losses,
        "winrate":    _pct(wins, decided),
        "points":     round(pts, 2),
        "avg_points": round(pts / n, 2) if n else 0.0,
        "r_total":    round(r_total, 2),
        "expectancy": round(r_total / len(rs), 3) if rs else None,
        "r_known":    len(rs),
        "top_symbol": top_sym,
        "top_share":  round(top_cnt / n, 3) if n else 0.0,
        "top2_share": round(top2_cnt / n, 3) if n else 0.0,
        "top2_names": " + ".join(nm for nm, _ in ranked[:2]),
        "symbols":    len(by_sym),
        "hhi":        round(hhi, 3),
        "_ids":       {r["id"] for r in rows},
    }


def _lever(rows: list, keyfn: Callable, total_points: float, total_r: float,
           lever_key: str = "", order: Optional[list] = None) -> list:
    """يشرّح القرارات حسب رافعة واحدة ويَسِم كل شريحة بحكم الحارس."""
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)

    out = []
    for value, grp in groups.items():
        s = _summarize(grp)
        s["value"] = value
        # الأثر المضاد: كم تصير الفترة لو أُزيلت هذه الشريحة بالكامل؟
        s["points_without"] = round(total_points - s["points"], 2)
        s["r_without"]      = round(total_r - s["r_total"], 2)

        reasons = []
        if s["n"] < MIN_N_SUGGEST:
            reasons.append("العينة %d < %d" % (s["n"], MIN_N_SUGGEST))

        # (2026-09-16) حين تكون الرافعة هي الرمز نفسه، هيمنة الرمز تعريف
        # لا تضليل — وإطلاق الإنذار عليها كان يَسِم كل صف بجدول الرموز
        # فيُعطّل الجدول بالكامل. التركّز يُفحص فقط للروافع الأخرى.
        if lever_key != "symbol" and s["n"] >= MIN_N_SHOW:
            if s["top_share"] > MAX_SYM_SHARE:
                reasons.append("%d%% منها %s — الحكم يقع على الرمز لا على الرافعة"
                               % (int(s["top_share"] * 100), s["top_symbol"]))
            elif s["top2_share"] > MAX_TOP2_SHARE and s["symbols"] > 1:
                # رمز واحد قد لا يتجاوز العتبة بينما رمزان يشكّلان الشريحة
                # كلها عملياً. hhi كان يُحسب ولا يُستخدم — هذه هي الثغرة.
                reasons.append("%d%% منها %s — رمزان يشكّلان الشريحة فعلياً"
                               % (int(s["top2_share"] * 100), s["top2_names"]))

        s["confounded"]       = bool(reasons)
        s["confound_reasons"] = reasons
        out.append(s)

    if order:
        idx = {v: i for i, v in enumerate(order)}
        out.sort(key=lambda x: idx.get(x["value"], 999))
    else:
        out.sort(key=lambda x: (x["expectancy"] if x["expectancy"] is not None else 99))
    return out


def _recommendations(levers: dict, labels: dict, total_r: float,
                     total_n: int, baseline_exp: Optional[float]) -> list:
    """
    يحوّل الشرائح إلى فرضيات — فقط ما نجا من الحارس، والحكم بـR لا بالنقاط.
    المقارنة نسبية بخط أساس النظام نفسه: شريحة سالبة داخل نظام سالب ليست
    استثناءً يُحذف، والعبرة بمقدار انحرافها عن باقي القرارات.
    """
    if baseline_exp is None:
        return []

    recs = []
    for lever_key, buckets in levers.items():
        for b in buckets:
            if b["confounded"] or b["n"] < MIN_N_SUGGEST or b["expectancy"] is None:
                continue
            exp   = b["expectancy"]
            share = (b["n"] / total_n) if total_n else 0.0
            delta = exp - baseline_exp

            if delta <= -EXP_MARGIN and exp < 0 and share >= 0.05:
                recs.append({
                    "action":     "تشديد",
                    "lever":      labels.get(lever_key, lever_key),
                    "lever_key":  lever_key,
                    "value":      b["value"],
                    "n":          b["n"],
                    "winrate":    b["winrate"],
                    "expectancy": exp,
                    "points":     b["points"],
                    "effect":     "توقّع %+.2fR مقابل %+.2fR عاماً — حذفها يرفع "
                                  "إجمالي الفترة إلى %+.2fR بدل %+.2fR"
                                  % (exp, baseline_exp, b["r_without"], total_r),
                    "strength":   "قوية" if b["n"] >= 25 else "مبدئية",
                    "caveat":     "أثر مقاس على الماضي لا وعد بالمستقبل — يُختبر قبل التثبيت.",
                    "_ids":       b["_ids"],
                })
            elif delta >= EXP_MARGIN and exp > 0.2 and share <= 0.25:
                recs.append({
                    "action":     "تخفيف",
                    "lever":      labels.get(lever_key, lever_key),
                    "lever_key":  lever_key,
                    "value":      b["value"],
                    "n":          b["n"],
                    "winrate":    b["winrate"],
                    "expectancy": exp,
                    "points":     b["points"],
                    "effect":     "توقّع %+.2fR مقابل %+.2fR عاماً — ونصيبها "
                                  "%.0f%% فقط من القرارات"
                                  % (exp, baseline_exp, share * 100),
                    "strength":   "قوية" if b["n"] >= 25 else "مبدئية",
                    "caveat":     "التخفيف يزيد العدد لا الجودة بالضرورة — الشريحة "
                                  "الجديدة قد لا تشبه القديمة. يُقاس بعد التطبيق.",
                    "_ids":       b["_ids"],
                })

    # (2026-09-16) تداخل الفرضيات. رافعات مختلفة قد تصف نفس الصفقات: أول
    # تشغيل حقيقي أعطى ثلاث فرضيات (وقف 0.30–0.50% ن=25، جلسة آسيا ن=30،
    # R/R 2.5–3.0 ن=30) من أصل 107 قرار — والعرض يوحي بأن آثارها تُجمع.
    # لا تُجمع إن كانت نفس الصفقات موصوفة ثلاث مرات. يُقاس ويُعلَن.
    for i, a in enumerate(recs):
        overlaps = []
        for j, b in enumerate(recs):
            if i == j:
                continue
            inter = len(a["_ids"] & b["_ids"])
            if not inter:
                continue
            sh = inter / min(len(a["_ids"]), len(b["_ids"]))
            if sh >= 0.5:
                overlaps.append("%s: %s (%d%% نفس الصفقات)"
                                % (b["lever"], b["value"], int(sh * 100)))
        a["overlaps"] = overlaps

    recs.sort(key=lambda r: (r["action"] != "تشديد", r["expectancy"]))
    for r in recs:
        r.pop("_ids", None)
    return recs


# ── نقطة الدخول ────────────────────────────────────────────────────────
def build_quality_report(db, days: int = 30) -> dict:
    from app.models.signal import Signal
    from app.services.decision_grouping import verified_unique_decisions

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    raw = db.query(Signal).filter(Signal.created_at >= cutoff).all()
    decisions = verified_unique_decisions(raw)

    # الحقول غير المتاحة بمخرجات التجميع تُجلب من الصف الممثِّل
    meta = {s.id: s for s in raw}

    enriched = []
    for d in decisions:
        s = meta.get(d["id"])
        if s is None:
            continue
        created = _utc(d.get("created_at"))
        exited  = _utc(d.get("exit_executed"))
        try:
            entry = float(s.entry_price or 0)
            sl    = float(s.stop_loss or 0)
        except (TypeError, ValueError):
            entry = sl = 0.0
        enriched.append({
            **d,
            "created":      created,
            "exited":       exited,
            "broadcast":    bool(s.broadcast_sent),
            "sl_pct":       (abs(entry - sl) / entry * 100) if entry else None,
            "r":            _r_multiple(s.entry_price, s.stop_loss,
                                        s.take_profit_1, s.take_profit_2, d["status"]),
            "killzone":     s.killzone or None,
            "wyckoff":      s.wyckoff_phase or None,
            "zone":         s.premium_discount or None,
            "duration_min": ((exited - created).total_seconds() / 60.0
                             if (created and exited and exited >= created) else None),
        })

    closed       = [d for d in enriched if d["status"] in CLOSED]
    total_points = round(sum(float(d["points"] or 0) for d in closed), 2)
    total_n      = len(closed)
    overall      = _summarize(closed)
    total_r      = overall["r_total"]

    # ── الفارق بين المقاس والقابل للتداول ──────────────────────────────
    unsent     = [d for d in closed if not d["broadcast"]]
    tradable   = [d for d in closed if d["broadcast"]]
    t          = _summarize(tradable)
    unsent_pts = round(sum(float(d["points"] or 0) for d in unsent), 2)

    # ── سلامة الأرقام ──────────────────────────────────────────────────
    conflicts = [d for d in enriched if d.get("status_conflict")]

    def coverage(field: str) -> dict:
        have = sum(1 for d in closed if d.get(field))
        return {"have": have, "total": total_n, "pct": _pct(have, total_n)}

    cov_kz, cov_wy, cov_zn = coverage("killzone"), coverage("wyckoff"), coverage("zone")
    r_cov = _pct(overall["r_known"], total_n)

    def cov_status(p: float) -> str:
        return "ok" if p >= 80 else ("warn" if p >= 30 else "bad")

    exp = overall["expectancy"]
    integrity = [
        {
            "key":    "expectancy",
            "label":  "توقّع النظام (متوسط R للقرار)",
            "value":  ("%+.3fR" % exp) if exp is not None else "—",
            "status": "ok" if (exp or 0) >= 0.15 else ("warn" if (exp or 0) > 0 else "bad"),
            "why":    "الرقم الوحيد الذي يحسم ربحية النظام: موجب ⇒ رابح على المدى، "
                      "وقرب الصفر ⇒ تعادل لا يصمد أمام السبريد والانزلاق. "
                      "النقاط قد تبدو كبيرة وهو سالب، لأن مضاعف النقاط يختلف "
                      "بين الرموز حتى 1200 ضعفاً.",
        },
        {
            "key":    "unbroadcast",
            "label":  "قرارات مُغلقة لم تُبثّ قط",
            "value":  "%d قراراً — %+.2f نقطة" % (len(unsent), unsent_pts),
            "status": "ok" if not unsent else
                      ("warn" if len(unsent) / max(total_n, 1) < 0.05 else "bad"),
            "why":    "نقاطها تدخل التقارير ولم يستطع أي مشترك تداولها — "
                      "الفارق بين رقم داخلي ورقم يصحّ عرضه على المشتركين.",
        },
        {
            "key":    "status_conflict",
            "label":  "قرارات اختلفت صفوفها بالحالة",
            "value":  "%d قراراً" % len(conflicts),
            "status": "ok" if not conflicts else "bad",
            "why":    "نفس القرار سُجّل بنتيجتين مختلفتين لمستخدمين مختلفين — "
                      "يعني أن الرصد غير حتمي، فلا يُعتمد على أي منهما.",
        },
        {
            "key":    "r_coverage",
            "label":  "تغطية حساب R",
            "value":  "%s%% (%d/%d)" % (r_cov, overall["r_known"], total_n),
            "status": cov_status(r_cov),
            "why":    "القرار بلا مستويات سليمة (وقف = دخول مثلاً) لا يُحسب له R "
                      "ويسقط من كل حكم — النقص هنا يعني أن التوقّع مبني على جزء.",
        },
        {
            "key":    "coverage_killzone",
            "label":  "تغطية حقل الجلسة (killzone)",
            "value":  "%s%% (%d/%d)" % (cov_kz["pct"], cov_kz["have"], cov_kz["total"]),
            "status": cov_status(cov_kz["pct"]),
            "why":    "لا تُحلَّل رافعة لا تُسجَّل. صفر تغطية ⇒ الحقل لا يُملأ إطلاقاً "
                      "عند الإنشاء، وجدول Killzone بلا معنى حتى يُصلَح.",
        },
        {
            "key":    "coverage_wyckoff",
            "label":  "تغطية حقل Wyckoff",
            "value":  "%s%% (%d/%d)" % (cov_wy["pct"], cov_wy["have"], cov_wy["total"]),
            "status": cov_status(cov_wy["pct"]),
            "why":    "أُصلح التقاطه مؤخراً، فالصفوف الأقدم فارغة بالضرورة — "
                      "النسبة سترتفع مع تراكم القرارات الجديدة وحدها.",
        },
        {
            "key":    "coverage_zone",
            "label":  "تغطية حقل Premium/Discount",
            "value":  "%s%% (%d/%d)" % (cov_zn["pct"], cov_zn["have"], cov_zn["total"]),
            "status": cov_status(cov_zn["pct"]),
            "why":    "نفس السبب.",
        },
        {
            "key":    "sample",
            "label":  "حجم العينة بالفترة",
            "value":  "%d قراراً مغلقاً من %d" % (total_n, len(enriched)),
            "status": "ok" if total_n >= 100 else ("warn" if total_n >= 40 else "bad"),
            "why":    "دون ~40 قراراً لا تُميَّز المهارة من الحظ. ومع تقسيمها على "
                      "11 رافعة تصغر كل شريحة، فمعظمها سيُوسم 'عينة صغيرة' — "
                      "وهذا سلوك صحيح لا قصور.",
        },
    ]

    # ── الروافع ────────────────────────────────────────────────────────
    def L(key, keyfn, order=None):
        return _lever(closed, keyfn, total_points, total_r, lever_key=key, order=order)

    levers = {
        "symbol":     L("symbol",     lambda d: d["market"]),
        "timeframe":  L("timeframe",  lambda d: d["timeframe"]),
        "direction":  L("direction",  lambda d: d["signal_type"]),
        "confidence": L("confidence", lambda d: _bucket(d.get("ai_confidence"), CONF_EDGES),
                        [l for _, l in CONF_EDGES]),
        "rr":         L("rr",         lambda d: _bucket(d.get("risk_reward_ratio"), RR_EDGES),
                        [l for _, l in RR_EDGES]),
        "stop":       L("stop",       lambda d: _bucket(d.get("sl_pct"), SL_EDGES),
                        [l for _, l in SL_EDGES]),
        "duration":   L("duration",   lambda d: _bucket(d.get("duration_min"), DUR_EDGES),
                        [l for _, l in DUR_EDGES]),
        "session":    L("session",    lambda d: _session(d["created"].hour if d["created"] else None)),
        "killzone":   L("killzone",   lambda d: d.get("killzone") or "غير مسجّل"),
        "wyckoff":    L("wyckoff",    lambda d: d.get("wyckoff") or "غير مسجّل"),
        "zone":       L("zone",       lambda d: d.get("zone") or "غير مسجّل"),
    }

    labels = {
        "symbol": "الرمز", "timeframe": "الفريم", "direction": "الاتجاه",
        "confidence": "الثقة", "rr": "R/R", "stop": "مسافة الوقف",
        "duration": "مدة الصفقة", "session": "الجلسة", "killzone": "Killzone",
        "wyckoff": "Wyckoff", "zone": "Premium/Discount",
    }

    # مدة الصفقة تُستبعد من الاقتراحات: غير معلومة وقت الإصدار فلا تصلح
    # شرطاً، وارتباطها بالربح فيه شقّ حسابي (الهدف الأبعد يستغرق وقتاً
    # أطول بالضرورة) لا استراتيجي. تبقى معروضة للتشخيص فقط.
    suggestable = {k: v for k, v in levers.items() if k != "duration"}
    recs = _recommendations(suggestable, labels, total_r, total_n, overall["expectancy"])

    for buckets in levers.values():
        for b in buckets:
            b.pop("_ids", None)

    return {
        "window_days":  days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds":   {
            "min_n_suggest":   MIN_N_SUGGEST,
            "max_symbol_share": MAX_SYM_SHARE,
            "max_top2_share":  MAX_TOP2_SHARE,
            "exp_margin":      EXP_MARGIN,
        },
        "headline": {
            "decisions_total":  len(enriched),
            "decisions_closed": total_n,
            "decisions_open":   len(enriched) - total_n,
            "winrate":          overall["winrate"],
            "points":           total_points,
            "avg_points":       overall["avg_points"],
            "expectancy":       overall["expectancy"],
            "r_total":          total_r,
            "tradable": {
                "decisions":  t["n"],
                "winrate":    t["winrate"],
                "points":     t["points"],
                "avg_points": t["avg_points"],
                "expectancy": t["expectancy"],
                "r_total":    t["r_total"],
            },
            "measurement_gap": {
                "decisions": len(unsent),
                "points":    unsent_pts,
                "share_pct": _pct(len(unsent), total_n),
            },
        },
        "integrity":       integrity,
        "lever_labels":    labels,
        "levers":          levers,
        "recommendations": recs,
        "unbroadcast_list": [
            {
                "id":         d["id"],
                "market":     d["market"],
                "timeframe":  d["timeframe"],
                "status":     d["status"],
                "points":     round(float(d["points"] or 0), 2),
                "r":          d["r"],
                "age_min":    round(d["duration_min"], 1) if d["duration_min"] is not None else None,
                "created_at": d["created"].isoformat() if d["created"] else None,
            }
            for d in sorted(
                unsent,
                key=lambda x: x["created"] or datetime.min.replace(tzinfo=timezone.utc),
            )
        ],
    }
