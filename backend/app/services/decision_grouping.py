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
        "market":          rep.market,
        "timeframe":       rep.timeframe,
        "signal_type":     rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type,
        "entry_price":     rep.entry_price,
        "status":          max(set(statuses), key=statuses.count),   # الأغلبية (عادةً كلهم متطابقين)
        "status_conflict": len(set(statuses)) > 1,
        "points":          rep.points_earned or 0,
        "exit_executed":   rep.exit_executed,
        "user_count":      len(rows),
    }
