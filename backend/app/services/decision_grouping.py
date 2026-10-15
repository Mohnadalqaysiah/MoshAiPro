"""
منطق تجميع "القرار الفريد" — مشترك بين:
  - app/api/admin.py           (تقارير الأداء المجمّعة — طبقة عرض)
  - app/services/ai_engine_v5.py (winrate الحقيقي المُستخدم بمعايرة العتبات الحية)

(2026-09-03) استُخرج لملف مشترك بدل نسختين منفصلتين، بعد ما تأكد إن نفس
المشكلة (عدّ كل صف Signal كصفقة مستقلة بدون تجميع) موجودة بالمكانين —
تفادياً لانحراف نسختين مستقلتين من نفس المنطق عن بعض مستقبلاً.

القرار الواحد (نفس السوق+الفريم+النوع+سعر الدخول) بيتحفظ كصف Signal
منفصل لكل مستخدم استلمه (كل مستخدم عنده صفقة/مركز مستقل بحسابه — هذا
صحيح وضروري لتاريخه الشخصي، ولا يُمس هون إطلاقاً). أي حساب مجمّع
(winrate، عدد الصفقات، نقاط) لازم يُحسب على مستوى القرار الفريد، وإلا
قرار واحد بُثّ لعدة مستخدمين يُحتسب عدة مرات بدل مرة.
"""
from datetime import datetime, timezone

# نافذة زمنية تفصل بين تكرارات نفس (سوق+فريم+نوع+سعر دخول) تُعتبر "نفس
# القرار" — monitor_watchlists (telegram-bot/bot.py) يحلل كل رمز مرة
# وحدة بالدورة ويعيد استخدام نفس النتيجة (نفس entry_price بالضبط) لكل
# مستخدم مراقب لنفس الرمز، فالتطابق الحرفي على السعر موثوق. النافذة
# الزمنية بس تفصل تكرارات بعيدة فعلاً (نادر، ممكن يرجع السعر لنفس
# المستوى بالضبط بعد ساعات — هذا قرار تاني، مو نفس القرار).
DECISION_GROUP_WINDOW_MIN = 2


def decision_key(market: str, timeframe: str, signal_type, entry_price: float) -> tuple:
    """مفتاح تجميع القرار (بدون البعد الزمني) — نفس المعيار المُستخدم
    بـgroup_unique_decisions، متاح لوحده للـdedup الحي (مثل check_outcomes
    ببوت.py) بدون الحاجة لتشغيل التجميع الكامل بكل استدعاء."""
    stype = signal_type.value if hasattr(signal_type, "value") else signal_type
    return (market, timeframe, stype, round(float(entry_price or 0), 5))


def group_unique_decisions(signals: list) -> list[dict]:
    """يُجمّع صفوف Signal (بيانات خام، لا تُعدَّل ولا تُحذف) إلى "قرارات
    فريدة". يُعيد قائمة dicts، كل عنصر = قرار واحد فيه:
      market, timeframe, signal_type, entry_price, status, points,
      exit_executed, user_count (كم صف/مستخدم بهالمجموعة), status_conflict
      (True لو صفوف المجموعة اختلفت بالنتيجة — حالة شاذة تستاهل تحقيق
      منفصل، منحسبها هون بس منُبلّغ عنها بدل ما نخفيها)."""
    buckets: dict[tuple, list] = {}
    for s in signals:
        key = decision_key(s.market, s.timeframe, s.signal_type, s.entry_price)
        buckets.setdefault(key, []).append(s)

    groups: list[dict] = []
    for key, rows in buckets.items():
        rows.sort(key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc))
        cluster: list = []
        for r in rows:
            if cluster:
                gap_min = abs(((r.created_at or cluster[-1].created_at) - cluster[-1].created_at).total_seconds()) / 60
                if gap_min > DECISION_GROUP_WINDOW_MIN:
                    groups.append(_finalize_decision_group(cluster))
                    cluster = []
            cluster.append(r)
        if cluster:
            groups.append(_finalize_decision_group(cluster))

    return groups


def _finalize_decision_group(rows: list) -> dict:
    statuses = [r.status.value if hasattr(r.status, "value") else r.status for r in rows]
    rep = rows[0]
    return {
        "id":              rep.id,
        "market":          rep.market,
        "timeframe":       rep.timeframe,
        "signal_type":     rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type,
        "entry_price":     rep.entry_price,
        # (2026-10-14) لمقارنة "نفس الصفقة" بـmerge_reissued — مفاتيح إضافية فقط، لا تغيّر أي سلوك قائم
        "stop_loss":       rep.stop_loss,
        "take_profit_1":   rep.take_profit_1,
        "expires_at":      getattr(rep, "expires_at", None),
        "status":          max(set(statuses), key=statuses.count),   # الأغلبية (عادةً كلهم متطابقين)
        "status_conflict": len(set(statuses)) > 1,
        "points":          rep.points_earned or 0,
        "risk_reward_ratio": rep.risk_reward_ratio,
        "ai_confidence":   rep.ai_confidence,
        "created_at":      rep.created_at,
        "exit_executed":   rep.exit_executed,
        "user_count":      len(rows),
        # (2026-09-21) حقل إضافي بحت — لا يمسّ أي مفتاح موجود ولا يغيّر
        # سلوك معايرة ai_engine_v5. لازم لمطابقة SignalDelivery بدقة:
        # rep هون أقدم صف بالمجموعة (rows[0] بعد ترتيب تصاعدي)، بينما
        # /bot/new-signals يبثّ عن أحدث صف — فالبحث بـid واحد بيخطئ الصف
        # الصحيح دائماً. الحل: كل معرّفات المجموعة، لا واحد مفترَض.
        "row_ids":         [r.id for r in rows],
    }


SAME_TRADE_ENTRY_TOL = 0.0005   # 0.05% — نفس عتبة حماية البث (_entries_equivalent بـbot.py)
SAME_TRADE_LEVEL_TOL = 0.25     # فرق الوقف ≤25% من المخاطرة، وفرق TP1 ≤25% من مسافة الهدف
_CLOSED = ("TP1_HIT", "TP2_HIT", "SL_HIT")
# (2026-10-15) إعادة إصدار بدخول مُعاد تسعيره: diag_near_duplicates — XRPUSD (دخول +0.09%) وNAS100 (+0.24%) بنفس الوقف
# والهدف حرفياً وصلتا للمشتركين مرتين وخسرتا مرتين. نفس الوقف (≤5% من المخاطرة) + نفس TP1 (≤25%) + دخول ≤0.5% = نفس الصفقة.
WIDE_ENTRY_TOL = 0.005
WIDE_SL_TOL = 0.05
MERGE_WIDE = True       # (15/10) مُفعَّل بعد معاينة diag_merge_preview.py wide: 635→621، 8 رابحة/7 خاسرة، +127.6R→+112.2R


def _same_levels(a: dict, d: dict) -> bool:
    """(2026-10-14) بلاغ AMD 13/10: صفقتان بنفس الدخول 587.87 لكن TP1 645.50 مقابل 593.43 —
    الأولى خسرت والثانية بلغت TP2، والدمج بالدخول وحده أخفى الرابحة عمّن استلمها. نفس الصفقة
    = نفس الدخول **والوقف والهدف**. إن غابت المستويات (بيانات قديمة) نكتفي بالدخول كما كان."""
    try:
        ea, sa, ta = float(a["entry_price"]), float(a["stop_loss"]), float(a["take_profit_1"])
        sd, td = float(d["stop_loss"]), float(d["take_profit_1"])
    except (KeyError, TypeError, ValueError):
        return True
    risk, reach = abs(ea - sa), abs(ta - ea)
    if not risk or not reach:
        return True
    return abs(sd - sa) <= SAME_TRADE_LEVEL_TOL * risk and abs(td - ta) <= SAME_TRADE_LEVEL_TOL * reach


def _same_trade_wide(a: dict, d: dict) -> bool:
    """نفس الوقف تقريباً حرفياً ونفس الهدف، والدخول ضمن 0.5% — الثانية إعادة تسعير لنفس الفكرة."""
    try:
        ea, sa, ta = float(a["entry_price"]), float(a["stop_loss"]), float(a["take_profit_1"])
        ed, sd, td = float(d["entry_price"]), float(d["stop_loss"]), float(d["take_profit_1"])
    except (KeyError, TypeError, ValueError):
        return False
    risk, reach = abs(ea - sa), abs(ta - ea)
    if not ea or not risk or not reach:
        return False
    return (abs(ed - ea) / ea <= WIDE_ENTRY_TOL and abs(sd - sa) <= WIDE_SL_TOL * risk
            and abs(td - ta) <= SAME_TRADE_LEVEL_TOL * reach)


def merge_reissued(decisions: list[dict], wide: bool = None) -> list[dict]:
    """(2026-10-12) يدمج "الصفقة المُعاد إصدارها" بالأولى: نفس الرمز والاتجاه، دخول ضمن
    0.05%، **ونفس الوقف والهدف** (_same_levels، 14/10)، أي فريم، وصدرت **والأولى ما زالت
    مفتوحة** (قبل exit_executed). تُحسب نتيجة
    الأولى — هي التي وصلت للمشتركين. القاعدة متماثلة على الرابح والخاسر (DECISIONS 12/10).

    لا تُستدعى من group_unique_decisions: معايرة المحرك (ai_engine_v5) تستخدم تلك
    مباشرة والمحرك مجمّد — الدمج طبقة عرض/إحصاء فوقها فقط.
    يضيف للقرار المُبقى: merged_count، merged_row_ids، merge_conflict (نتيجتان مختلفتان)."""
    far = datetime.max.replace(tzinfo=timezone.utc)
    use_wide = MERGE_WIDE if wide is None else wide

    def _aware(d):
        return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)

    kept: list[dict] = []
    for d in sorted(decisions, key=lambda x: _aware(x.get("created_at")) or far):
        created = _aware(d.get("created_at"))
        host = None
        if created is not None and d.get("entry_price"):
            for a in reversed(kept):
                if a["market"] != d["market"] or a["signal_type"] != d["signal_type"]:
                    continue
                a_entry = float(a.get("entry_price") or 0)
                narrow = bool(a_entry) and abs(float(d["entry_price"]) - a_entry) / a_entry <= SAME_TRADE_ENTRY_TOL                     and _same_levels(a, d)
                if not narrow and not (use_wide and _same_trade_wide(a, d)):
                    continue
                a_created = _aware(a.get("created_at"))
                # (2026-10-14) الأولى "مفتوحة" حتى إغلاقها أو انتهاء مدتها — لا للأبد. قبلها صفقة منتهية بلا
                # نتيجة (exit_executed فارغ) كانت تبتلع كل إعادة إصدار بنفس المستويات لأيام (USDJPY 9→13/10).
                a_exit = _aware(a.get("exit_executed")) or _aware(a.get("expires_at")) or far
                if a_created is not None and a_created <= created < a_exit:
                    host = a
                    break
        if host is None:
            d = dict(d, merged_count=0, merged_row_ids=[], merge_conflict=False)
            kept.append(d)
        else:
            host["merged_count"] += 1
            host["merged_row_ids"] += d.get("row_ids", [d["id"]])
            host["user_count"] = host.get("user_count", 0) + d.get("user_count", 0)
            if host["status"] not in _CLOSED and d["status"] in _CLOSED:
                # (2026-10-14) الأولى انتهت بلا هدف ولا وقف والنسخة اللاحقة أُغلقت فعلاً (وأُبلغ مستلموها
                # بنتيجتها) ← تُعرض النتيجة الحقيقية، ربحاً أو خسارة. وإلا اختفت خسارة USDJPY التي وصلت 107 مشتركين.
                keep = ("merged_count", "merged_row_ids", "user_count", "row_ids", "created_at")
                host.update({k: v for k, v in d.items() if k not in keep})
                host["adopted_outcome"] = True
            elif d["status"] in _CLOSED and host["status"] in _CLOSED and d["status"] != host["status"]:
                host["merge_conflict"] = True
    return kept


def verified_unique_decisions(signals: list) -> list[dict]:
    """الأداة الجاهزة لأي تقرير/إحصائية مجمّعة: تفلتر الصفوف الخام لمصدرها
    الموثوق فقط (current_price IS NOT NULL — تلقائي عبر check_outcomes،
    مو تحديد يدوي غير متحقق منه، راجع set_signal_outcome بـadmin.py)،
    وتُجمّعها لقرارات فريدة عبر group_unique_decisions(). استُخدمت هون
    بدل التكرار المباشر على signals الخام بكل مكان بالمشروع كان يحسب
    winrate/نقاط/عدد صفقات (signals.py, bot.py, markets.py — راجع
    commit 2026-09-03 اللي أضافها لكل هالمواقع دفعة وحدة بعد ما تأكد
    إنها نفس المشكلة بالضبط بعدة مواقع مستقلة)."""
    # (2026-09-10) نشمل التصحيحات اليدوية المؤكدة بالسعر (outcome_verified)
    # جنب الرصد التلقائي (current_price IS NOT NULL). التصحيح اليدوي القديم
    # غير المؤكد (الاثنين False/NULL) يبقى مستبعداً. معايرة المحرك
    # (load_performance_from_db) ما تستخدم هالدالة — تبقى صارمة على التلقائي.
    verified = [
        s for s in signals
        if s.current_price is not None or getattr(s, "outcome_verified", False)
    ]
    # (2026-10-12) + دمج الصفقة المُعاد إصدارها وهي مفتوحة — معاينة diag_merge_preview.py:
    # 604→537 قراراً، مجموع R شبه ثابت (+155.8→+157.0)، ودمجت رابحات وخاسرات معاً
    # (W41 انخفض). معايرة المحرك لا تمر من هنا (تستدعي group_unique_decisions مباشرة).
    return merge_reissued(group_unique_decisions(verified))
