"""
analyze_min_rr_simulation.py
=============================
محاكاة قراءة فقط (لا تعديل، لا كتابة بقاعدة البيانات) — تجاوب على:
هل رفع _get_min_rr() من 1.0 لـ1.3 أو 1.5 كان سيحسّن أو يسوء النتيجة؟

يستخدم verified_unique_decisions() الحيّة من decision_grouping.py (نفس
المنطق المستخدم بكل تقرير أداء بالمنصة) و risk_reward_ratio المخزّن فعلياً
وقت إنشاء كل قرار (نفس الرقم اللي _institutional_gate يحسبه ويقارنه
بـ_get_min_rr() — لا إعادة حساب، رقم حقيقي من حينها).

التشغيل (قراءة فقط، آمن 100%):
  docker cp analyze_min_rr_simulation.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_min_rr_simulation.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}


def bucket_for(rr: float) -> str:
    if rr < 1.3:
        return "1.0-1.3"
    elif rr < 1.8:
        return "1.3-1.8"
    else:
        return ">1.8"


def summarize(decisions: list, label: str):
    n = len(decisions)
    if n == 0:
        print(f"  {label}: (فارغ)")
        return
    wins = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
    losses = sum(1 for d in decisions if d["status"] == "SL_HIT")
    pts = sum(d["points"] for d in decisions)
    winrate = wins / n * 100 if n else 0
    print(f"  {label}: n={n:4d}  رابحة={wins:4d}  خاسرة={losses:4d}  "
          f"winrate={winrate:5.1f}%  مجموع_نقاط={pts:+9.2f}  متوسط/قرار={pts/n:+7.2f}")


def main():
    db = SessionLocal()
    try:
        signals = (
            db.query(Signal)
            .filter(Signal.created_at >= CUTOFF)
            .all()
        )
        print(f"📊 صفوف خام منذ {CUTOFF.date()}: {len(signals)}")

        decisions = verified_unique_decisions(signals)
        print(f"📊 قرارات فريدة (بعد التجميع + فلتر current_price/outcome_verified): {len(decisions)}")

        closed = [d for d in decisions if d["status"] in CLOSED]
        print(f"📊 قرارات محسومة (TP/SL فقط، تستبعد ACTIVE/EXPIRED): {len(closed)}")

        with_rr = [d for d in closed if d["risk_reward_ratio"] is not None]
        missing_rr = len(closed) - len(with_rr)
        print(f"📊 من هذي، عندها risk_reward_ratio مسجّل: {len(with_rr)}  "
              f"(ناقص/None: {missing_rr} — مستبعدة من التبويب حسب RR)")

        print("\n" + "="*78)
        print("1) التوزيع حسب فئة RR الفعلي (RR الحقيقي وقت إنشاء القرار)")
        print("="*78)
        buckets: dict[str, list] = {"1.0-1.3": [], "1.3-1.8": [], ">1.8": []}
        for d in with_rr:
            buckets[bucket_for(float(d["risk_reward_ratio"]))].append(d)
        for label in ("1.0-1.3", "1.3-1.8", ">1.8"):
            summarize(buckets[label], f"RR {label}")

        print("\n" + "-"*78)
        print("توزيع الرموز المتكررة بخسائر صغيرة (NATGAS/ARAMCO/COPPER/SOLUSD) عبر الفئات:")
        watch_symbols = {"NATGAS", "ARAMCO", "COPPER", "SOLUSD"}
        for label in ("1.0-1.3", "1.3-1.8", ">1.8"):
            watch = [d for d in buckets[label] if d["market"] in watch_symbols]
            if watch:
                w_losses = sum(1 for d in watch if d["status"] == "SL_HIT")
                print(f"  RR {label}: {len(watch)} قرار من هالرموز، منها {w_losses} خاسرة")
            else:
                print(f"  RR {label}: لا يوجد")

        print("\n" + "="*78)
        print("2) و3) محاكاة رفع _get_min_rr — لا تعديل فعلي، قراءة فقط")
        print("="*78)

        baseline_pts = sum(d["points"] for d in with_rr)
        baseline_n   = len(with_rr)
        baseline_wins = sum(1 for d in with_rr if d["status"] in ("TP1_HIT", "TP2_HIT"))
        print(f"\n📌 الوضع الحالي (RR_min=1.0 فعلياً — كل شيء بعينة with_rr):")
        print(f"   n={baseline_n}  winrate={baseline_wins/baseline_n*100:.1f}%  "
              f"مجموع_نقاط={baseline_pts:+.2f}  expectancy/قرار={baseline_pts/baseline_n:+.3f}")

        for threshold in (1.3, 1.5):
            kept     = [d for d in with_rr if float(d["risk_reward_ratio"]) >= threshold]
            rejected = [d for d in with_rr if float(d["risk_reward_ratio"]) <  threshold]
            rej_wins   = [d for d in rejected if d["status"] in ("TP1_HIT", "TP2_HIT")]
            rej_losses = [d for d in rejected if d["status"] == "SL_HIT"]
            rej_win_pts  = sum(d["points"] for d in rej_wins)
            rej_loss_pts = sum(d["points"] for d in rej_losses)
            kept_pts = sum(d["points"] for d in kept)
            kept_n   = len(kept)
            kept_wins = sum(1 for d in kept if d["status"] in ("TP1_HIT", "TP2_HIT"))

            print(f"\n📌 سيناريو RR_min={threshold}:")
            print(f"   قرارات كانت سترفض (RR < {threshold}): {len(rejected)} "
                  f"من أصل {baseline_n} ({len(rejected)/baseline_n*100:.1f}%)")
            print(f"     منها رابحة فعلياً (تضحية حقيقية): {len(rej_wins)}  "
                  f"مجموع نقاطها الضائعة={rej_win_pts:+.2f}")
            print(f"     منها خاسرة فعلياً (توفير حقيقي):  {len(rej_losses)}  "
                  f"مجموع نقاطها الموفّرة={-rej_loss_pts:+.2f}")
            if kept_n:
                print(f"   القرارات المتبقية (RR >= {threshold}): n={kept_n}  "
                      f"winrate={kept_wins/kept_n*100:.1f}%  "
                      f"مجموع_نقاط={kept_pts:+.2f}  expectancy/قرار={kept_pts/kept_n:+.3f}")
            else:
                print(f"   ⚠️  لا يوجد أي قرار متبقٍ بهالسيناريو — عينة فارغة")

        print("\n" + "="*78)
        print("4) تحذير حجم العينة")
        print("="*78)
        print(f"   إجمالي القرارات المستخدمة بالتبويب: {len(with_rr)}")
        if len(with_rr) < 100:
            print("   ⚠️  عينة صغيرة (<100) — أي فرق نسبة نجاح بين الفئات قد يكون")
            print("       ضجيجاً إحصائياً، مو نمطاً حقيقياً. لا تُبنى قرارات نهائية عليها لوحدها.")
        for label in ("1.0-1.3", "1.3-1.8", ">1.8"):
            if 0 < len(buckets[label]) < 20:
                print(f"   ⚠️  فئة RR {label} فيها {len(buckets[label])} قرار فقط — صغيرة جداً للاعتماد عليها منفردة.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
