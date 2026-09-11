"""
analyze_adausd_sl_cap.py
==========================
محاكاة قراءة فقط (لا تعديل، لا كتابة بقاعدة البيانات) — نفس أسلوب باكتيست
سقف SL المستخدم مع XAUUSD/XAGUSD (SL_DISTANCE_EXCEEDS_CAP بـai_engine_v5.py)،
مطبّق على ADAUSD بسقوف 0.7% / 1.0% / 1.3% (كريبتو أوسع تذبذباً من المعادن).

⚠️ عيّنة صغيرة جداً بطبيعتها (5 صفقات ADAUSD إجمالي بكل الفترة) — أي نتيجة
هون "مؤشر أولي فقط"، ليست بنفس ثقة تحليل الذهب (كان مبني على عينة أكبر
بكثير). السكربت نفسه يطبع هالتحذير أيضاً.

التشغيل (قراءة فقط، آمن 100%):
  docker cp analyze_adausd_sl_cap.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_adausd_sl_cap.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
SYMBOL = "ADAUSD"
CAPS = [0.007, 0.010, 0.013]   # 0.7% / 1.0% / 1.3%


def main():
    db = SessionLocal()
    try:
        signals = (
            db.query(Signal)
            .filter(Signal.created_at >= CUTOFF, Signal.market == SYMBOL)
            .all()
        )
        decisions = verified_unique_decisions(signals)
        closed = [d for d in decisions if d["status"] in CLOSED]

        print(f"📊 {SYMBOL} — قرارات فريدة منذ {CUTOFF.date()}: {len(decisions)}  "
              f"محسومة (TP/SL): {len(closed)}")

        if len(closed) < 15:
            print(f"\n⚠️  عيّنة صغيرة جداً ({len(closed)} قرار محسوم) — أقل بكثير من عينة")
            print("    تحليل الذهب الأصلي. أي نتيجة هون مؤشر أولي فقط، ليست قراراً نهائياً.")
            print("    لا تُطبَّق أي قاعدة جديدة بناءً على هذا وحده.\n")

        if not closed:
            print("لا توجد صفقات ADAUSD محسومة بهذي الفترة — لا يمكن إجراء المحاكاة.")
            return

        ids = [d["id"] for d in closed]
        rows = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(ids)).all()}

        # ── جدول كل الصفقات مع مسافة SL٪ ────────────────────────────────────
        print("\n" + "="*90)
        print("كل صفقات ADAUSD المحسومة بالفترة:")
        print("="*90)
        enriched = []
        for d in closed:
            r = rows.get(d["id"])
            if not r or not r.entry_price or not r.stop_loss:
                continue
            entry = float(r.entry_price)
            sl    = float(r.stop_loss)
            sl_pct = abs(entry - sl) / entry
            enriched.append({**d, "sl_pct": sl_pct, "entry": entry, "sl": sl})
            print(f"  #{d['id']:5d}  {d['status']:8s}  entry={entry:.5f}  sl={sl:.5f}  "
                  f"sl_dist={sl_pct*100:.3f}%  points={d['points']:+.2f}")

        print("\n" + "="*90)
        print("محاكاة سقوف SL (نفس أسلوب باكتيست XAUUSD/XAGUSD)")
        print("="*90)

        for cap in CAPS:
            rejected = [d for d in enriched if d["sl_pct"] > cap]
            kept     = [d for d in enriched if d["sl_pct"] <= cap]
            rej_wins   = [d for d in rejected if d["status"] in ("TP1_HIT", "TP2_HIT")]
            rej_losses = [d for d in rejected if d["status"] == "SL_HIT"]
            rej_win_pts  = sum(d["points"] for d in rej_wins)
            rej_loss_pts = sum(d["points"] for d in rej_losses)

            print(f"\n📌 سقف {cap*100:.1f}%:")
            print(f"   كانت سترفض: {len(rejected)} من أصل {len(enriched)}")
            if rejected:
                for d in rejected:
                    tag = "❌ خسارة (توفير حقيقي)" if d["status"] == "SL_HIT" else "✅ ربح (تضحية حقيقية)"
                    print(f"     #{d['id']} {d['status']:8s} sl_dist={d['sl_pct']*100:.3f}%  "
                          f"points={d['points']:+.2f}  → {tag}")
            print(f"   من المرفوضة: رابحة (تضحية)={len(rej_wins)} (نقاط مفقودة={rej_win_pts:+.2f})  "
                  f"خاسرة (توفير)={len(rej_losses)} (نقاط موفّرة={-rej_loss_pts:+.2f})")

            if kept:
                kept_wins = sum(1 for d in kept if d["status"] in ("TP1_HIT", "TP2_HIT"))
                kept_pts  = sum(d["points"] for d in kept)
                print(f"   الباقي بعد الرفض: n={len(kept)}  winrate={kept_wins/len(kept)*100:.1f}%  "
                      f"مجموع_نقاط={kept_pts:+.2f}  expectancy/قرار={kept_pts/len(kept):+.3f}")
            else:
                print("   ⚠️  لا يبقى أي قرار بهالسقف — عينة فارغة تماماً")

        baseline_pts = sum(d["points"] for d in enriched)
        baseline_wins = sum(1 for d in enriched if d["status"] in ("TP1_HIT", "TP2_HIT"))
        print(f"\n📌 الوضع الحالي (بدون أي سقف): n={len(enriched)}  "
              f"winrate={baseline_wins/len(enriched)*100:.1f}%  "
              f"مجموع_نقاط={baseline_pts:+.2f}  expectancy/قرار={baseline_pts/len(enriched):+.3f}")

        print("\n" + "="*90)
        print("⚠️ تذكير: عينة ADAUSD صغيرة جداً (n={}) — أي نتيجة هون مؤشر أولي، "
              "مش قرار نهائي، بعكس تحليل الذهب الأوسع.".format(len(enriched)))
        print("="*90)

    finally:
        db.close()


if __name__ == "__main__":
    main()
