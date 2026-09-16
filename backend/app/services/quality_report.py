"""
quality_report.py — تقرير جودة القرارات (قراءة محضة)
=======================================================
يجيب سؤالاً مختلفاً عن /admin/diagnostic. ذاك يفحص الـpipeline الحيّ
("لماذا لا تُولَّد إشارات الآن؟"). هذا يفحص السجل التاريخي:
"هل ما نقيسه صحيح، وأي شرط يستحق التشديد أو التخفيف؟"

مبادئ ثلاثة تحكم هذا الملف، كلها مستخلَصة من أخطاء وقعت فعلاً بهذا
المشروع لا من اعتبارات نظرية:

 1) القرار الفريد لا الصف. نفس القرار يُحفظ صفاً لكل مستخدم استلمه،
    فالعدّ الخام يضخّم كل شيء بمعامل عدد المستخدمين. المرجع الموحّد
    هو decision_grouping.verified_unique_decisions.

 2) لا اقتراح بلا حارس تضليل. الاقتراح "احذف كذا" يبدو مقنعاً دائماً
    لأن أي شريحة أسوأ من المتوسط موجودة حتماً. سابقاً بهذه الجلسة كاد
    تحليل مسافة الوقف يُفقد رمزاً رابحاً لأن الشريحة كان يهيمن عليها
    رمز واحد، والحكم كان يقع على الرمز لا على الرافعة. لذلك كل شريحة
    تحمل hhi ونصيب الرمز المهيمن، وتُوسم confounded ولا تتحول لاقتراح
    إن تجاوزت العتبة أو قلّت عينتها.

 3) الفرق بين "مقاس" و"قابل للتداول". قرار أُغلق قبل أن يُبثّ تُحتسب
    نقاطه بالتقارير ولم يستطع أي مشترك تداوله. الرقم الذي يُعرض
    للمشتركين يجب أن يكون الثاني. يُحسب هنا صراحةً كفارق.

لا شبكة، لا كتابة، لا مسّ للمحرك — كله من قاعدة البيانات.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

WIN    = {"TP1_HIT", "TP2_HIT"}
LOSS   = {"SL_HIT"}
CLOSED = WIN | LOSS

# عتبات الحارس — محافِظة عمداً. الخطأ باتجاه "لا اقتراح" يُصلحه جمع
# بيانات أكثر؛ والخطأ باتجاه اقتراح مضلِّل يُنفَّذ على الاستراتيجية ولا
# يُكتشف إلا بعد أسابيع من الضرر.
MIN_N_SUGGEST = 10     # أقل عينة يجوز بناء اقتراح عليها
MIN_N_SHOW    = 3      # أقل عينة تُقرأ أصلاً
MAX_SYM_SHARE = 0.60   # نصيب رمز واحد يتجاوزه ⇒ الحكم على الرمز لا الرافعة


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


# ── نواة التجميع ───────────────────────────────────────────────────────
def _summarize(rows: list) -> dict:
    """ملخّص مجموعة قرارات: عدد، ربح/خسارة، نقاط، وهيمنة الرموز."""
    n      = len(rows)
    wins   = sum(1 for r in rows if r["status"] in WIN)
    losses = sum(1 for r in rows if r["status"] in LOSS)
    pts    = sum(float(r["points"] or 0) for r in rows)

    by_sym = defaultdict(int)
    for r in rows:
        by_sym[r["market"]] += 1
    top_sym, top_cnt = "—", 0
    if by_sym:
        top_sym, top_cnt = max(by_sym.items(), key=lambda kv: kv[1])
    # مؤشر هيرفندال: 1.0 = رمز واحد فقط، وكلما قلّ زاد التنوّع
    hhi = sum((c / n) ** 2 for c in by_sym.values()) if n else 0.0

    decided = wins + losses
    return {
        "n":          n,
        "wins":       wins,
        "losses":     losses,
        "winrate":    _pct(wins, decided),
        "points":     round(pts, 2),
        "avg_points": round(pts / n, 2) if n else 0.0,
        "top_symbol": top_sym,
        "top_share":  round(top_cnt / n, 3) if n else 0.0,
        "symbols":    len(by_sym),
        "hhi":        round(hhi, 3),
    }


def _lever(rows: list, keyfn: Callable, total_points: float,
           order: Optional[list] = None) -> list:
    """يشرّح القرارات حسب رافعة واحدة ويَسِم كل شريحة بحكم الحارس."""
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)

    out = []
    for value, grp in groups.items():
        s = _summarize(grp)
        s["value"] = value
        # الأثر المضاد: كم تصير نقاط الفترة لو أُزيلت هذه الشريحة بالكامل؟
        s["points_without"] = round(total_points - s["points"], 2)

        reasons = []
        if s["n"] < MIN_N_SUGGEST:
            reasons.append("العينة %d < %d" % (s["n"], MIN_N_SUGGEST))
        if s["top_share"] > MAX_SYM_SHARE and s["n"] >= MIN_N_SHOW:
            reasons.append(
                "%d%% منها %s — الحكم يقع على الرمز لا على الرافعة"
                % (int(s["top_share"] * 100), s["top_symbol"])
            )
        s["confounded"]       = bool(reasons)
        s["confound_reasons"] = reasons
        out.append(s)

    if order:
        idx = {v: i for i, v in enumerate(order)}
        out.sort(key=lambda x: idx.get(x["value"], 999))
    else:
        out.sort(key=lambda x: x["points"])
    return out


def _recommendations(levers: dict, labels: dict,
                     total_points: float, total_n: int) -> list:
    """
    يحوّل الشرائح إلى اقتراحات — فقط ما نجا من الحارس.
    لا يقترح تعديلاً على المحرك؛ يقترح فرضية للاختبار مع أثرها المقاس.
    """
    overall_avg = round(total_points / total_n, 2) if total_n else 0.0
    recs = []
    for lever_key, buckets in levers.items():
        for b in buckets:
            if b["confounded"] or b["n"] < MIN_N_SUGGEST:
                continue
            share = (b["n"] / total_n) if total_n else 0.0

            if b["points"] < 0 and b["avg_points"] <= -3 and share >= 0.05:
                recs.append({
                    "action":   "تشديد",
                    "lever":    labels.get(lever_key, lever_key),
                    "value":    b["value"],
                    "n":        b["n"],
                    "winrate":  b["winrate"],
                    "points":   b["points"],
                    "effect":   "نقاط الفترة تصير %+.2f بدل %+.2f"
                                % (b["points_without"], total_points),
                    "strength": "قوية" if b["n"] >= 25 else "مبدئية",
                    "caveat":   "أثر مقاس على الماضي لا وعد بالمستقبل — يُختبر قبل التثبيت.",
                })
            elif b["avg_points"] >= 10 and b["winrate"] >= 55 and share <= 0.25:
                recs.append({
                    "action":   "تخفيف",
                    "lever":    labels.get(lever_key, lever_key),
                    "value":    b["value"],
                    "n":        b["n"],
                    "winrate":  b["winrate"],
                    "points":   b["points"],
                    "effect":   "متوسط %+.2f نقطة/قرار مقابل %+.2f عاماً — نصيبها %.0f%% فقط"
                                % (b["avg_points"], overall_avg, share * 100),
                    "strength": "قوية" if b["n"] >= 25 else "مبدئية",
                    "caveat":   "التخفيف يزيد العدد لا الجودة بالضرورة — الشريحة الجديدة "
                                "قد لا تشبه القديمة. يُقاس بعد التطبيق.",
                })
    recs.sort(key=lambda r: (r["action"] != "تشديد", -abs(r["points"])))
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

    # ── الفارق بين المقاس والقابل للتداول ──────────────────────────────
    unsent       = [d for d in closed if not d["broadcast"]]
    tradable     = [d for d in closed if d["broadcast"]]
    t            = _summarize(tradable)
    unsent_pts   = round(sum(float(d["points"] or 0) for d in unsent), 2)

    # ── سلامة الأرقام ──────────────────────────────────────────────────
    conflicts = [d for d in enriched if d.get("status_conflict")]

    def coverage(field: str) -> dict:
        have = sum(1 for d in closed if d.get(field))
        return {"have": have, "total": total_n, "pct": _pct(have, total_n)}

    cov_kz, cov_wy, cov_zn = coverage("killzone"), coverage("wyckoff"), coverage("zone")

    def cov_status(p: float) -> str:
        return "ok" if p >= 80 else ("warn" if p >= 30 else "bad")

    integrity = [
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
            "key":    "coverage_killzone",
            "label":  "تغطية حقل الجلسة (killzone)",
            "value":  "%s%% (%d/%d)" % (cov_kz["pct"], cov_kz["have"], cov_kz["total"]),
            "status": cov_status(cov_kz["pct"]),
            "why":    "لا يمكن تحليل رافعة لا تُسجَّل. النقص يعني أن تشريح "
                      "الجلسة مبني على جزء من البيانات لا كلها.",
        },
        {
            "key":    "coverage_wyckoff",
            "label":  "تغطية حقل Wyckoff",
            "value":  "%s%% (%d/%d)" % (cov_wy["pct"], cov_wy["have"], cov_wy["total"]),
            "status": cov_status(cov_wy["pct"]),
            "why":    "نفس السبب — أُصلح التقاطه مؤخراً، فالصفوف الأقدم فارغة بالضرورة.",
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
            "why":    "دون ~40 قراراً لا تُميَّز المهارة من الحظ، وأي اقتراح "
                      "مبني عليها يقارب التخمين.",
        },
    ]

    # ── الروافع ────────────────────────────────────────────────────────
    levers = {
        "symbol":     _lever(closed, lambda d: d["market"], total_points),
        "timeframe":  _lever(closed, lambda d: d["timeframe"], total_points),
        "direction":  _lever(closed, lambda d: d["signal_type"], total_points),
        "confidence": _lever(closed, lambda d: _bucket(d.get("ai_confidence"), CONF_EDGES),
                             total_points, [l for _, l in CONF_EDGES]),
        "rr":         _lever(closed, lambda d: _bucket(d.get("risk_reward_ratio"), RR_EDGES),
                             total_points, [l for _, l in RR_EDGES]),
        "stop":       _lever(closed, lambda d: _bucket(d.get("sl_pct"), SL_EDGES),
                             total_points, [l for _, l in SL_EDGES]),
        "duration":   _lever(closed, lambda d: _bucket(d.get("duration_min"), DUR_EDGES),
                             total_points, [l for _, l in DUR_EDGES]),
        "session":    _lever(closed, lambda d: _session(d["created"].hour if d["created"] else None),
                             total_points),
        "killzone":   _lever(closed, lambda d: d.get("killzone") or "غير مسجّل", total_points),
        "wyckoff":    _lever(closed, lambda d: d.get("wyckoff") or "غير مسجّل", total_points),
        "zone":       _lever(closed, lambda d: d.get("zone") or "غير مسجّل", total_points),
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
    recs = _recommendations(suggestable, labels, total_points, total_n)

    return {
        "window_days":  days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds":   {"min_n_suggest": MIN_N_SUGGEST, "max_symbol_share": MAX_SYM_SHARE},
        "headline": {
            "decisions_total":  len(enriched),
            "decisions_closed": total_n,
            "decisions_open":   len(enriched) - total_n,
            "winrate":          overall["winrate"],
            "points":           total_points,
            "avg_points":       overall["avg_points"],
            "tradable": {
                "decisions":  t["n"],
                "winrate":    t["winrate"],
                "points":     t["points"],
                "avg_points": t["avg_points"],
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
                "age_min":    round(d["duration_min"], 1) if d["duration_min"] is not None else None,
                "created_at": d["created"].isoformat() if d["created"] else None,
            }
            for d in sorted(
                unsent,
                key=lambda x: x["created"] or datetime.min.replace(tzinfo=timezone.utc),
            )
        ],
    }
