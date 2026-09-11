"""
analyze_tail_loss_concentration.py
====================================
محاكاة/تحليل قراءة فقط (لا تعديل، لا كتابة بقاعدة البيانات) — يجاوب على:
هل فيه رموز غير XAUUSD/XAGUSD عندها نفس نمط "صفقة أو صفقتين شاذة بوقف
واسع جداً بتسحب مجموع النقاط للأسفل"؟

يستخدم verified_unique_decisions() الحيّة (نفس منطق كل تقرير أداء بالمنصة).

التشغيل (قراءة فقط، آمن 100%):
  docker cp analyze_tail_loss_concentration.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_tail_loss_concentration.py
"""
import sys, math
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
ALREADY_CAPPED = {"XAUUSD", "XAGUSD"}   # عندها سقف SL فعلاً — مستبعدة من المرشحين


def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = verified_unique_decisions(signals)
        closed  = [d for d in decisions if d["status"] in CLOSED]
        losing  = [d for d in closed if d["points"] < 0]
        print(f"📊 قرارات فريدة منذ {CUTOFF.date()}: {len(decisions)}  "
              f"محسومة: {len(closed)}  خاسرة: {len(losing)}")

        if not losing:
            print("لا توجد قرارات خاسرة بهذي الفترة.")
            return

        total_loss_abs = sum(abs(d["points"]) for d in losing)
        losing_sorted   = sorted(losing, key=lambda d: d["points"])   # الأكبر خسارة أولاً

        top_n = max(1, math.ceil(len(losing_sorted) * 0.10))
        top10 = losing_sorted[:top_n]
        top10_loss_abs = sum(abs(d["points"]) for d in top10)
        pct = (top10_loss_abs / total_loss_abs * 100) if total_loss_abs else 0

        print("\n" + "="*90)
        print("1) تركّز الخسارة بأعلى 10% من الصفقات الخاسرة")
        print("="*90)
        print(f"إجمالي الخسارة (كل {len(losing_sorted)} قرار خاسر): {-total_loss_abs:.2f} نقطة")
        print(f"أعلى 10% ({top_n} قرار): {-top10_loss_abs:.2f} نقطة = {pct:.1f}% من إجمالي الخسارة\n")
        for d in top10:
            print(f"  #{d['id']:5d}  {d['market']:12s} {d['timeframe']:4s}  "
                  f"{d['status']:8s}  points={d['points']:+9.2f}  entry={d['entry_price']}")

        # ── جلب entry/stop_loss الحقيقيين للقرارات بأعلى 10% ──────────────────
        ids = [d["id"] for d in top10]
        rep_rows = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(ids)).all()}

        # ── متوسط مسافة SL٪ لكل رمز، محسوب من كل قراراته بنفس الفترة (أي حالة) ──
        by_symbol_all_ids: dict[str, list] = {}
        for d in decisions:
            by_symbol_all_ids.setdefault(d["market"], []).append(d["id"])

        all_ids = {i for ids_ in by_symbol_all_ids.values() for i in ids_}
        all_rows = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(all_ids)).all()}

        def sl_pct(row) -> float | None:
            if row and row.entry_price and row.stop_loss:
                return abs(float(row.entry_price) - float(row.stop_loss)) / float(row.entry_price) * 100
            return None

        print("\n" + "="*90)
        print("2) مسافة SL للصفقة الشاذة مقابل متوسط باقي صفقات نفس الرمز")
        print("="*90)

        candidates: dict[str, list] = {}
        for d in top10:
            sym = d["market"]
            if sym in ALREADY_CAPPED:
                print(f"\n{sym} (#{d['id']}) — مستبعد: عنده سقف SL فعلاً (معالج سابقاً).")
                continue
            rep = rep_rows.get(d["id"])
            this_pct = sl_pct(rep)
            if this_pct is None:
                print(f"\n{sym} (#{d['id']}) — بيانات ناقصة (entry/SL)، تخطّي.")
                continue

            other_ids = [i for i in by_symbol_all_ids.get(sym, []) if i != d["id"]]
            other_pcts = [p for i in other_ids if (p := sl_pct(all_rows.get(i))) is not None]
            avg_other = sum(other_pcts) / len(other_pcts) if other_pcts else None
            ratio = (this_pct / avg_other) if avg_other else None

            print(f"\n{sym} (#{d['id']}, {d['status']}, points={d['points']:+.2f}):")
            print(f"  مسافة SL لهذي الصفقة: {this_pct:.3f}% من سعر الدخول")
            if avg_other is not None:
                ratio_txt = f"{ratio:.1f}x" if ratio else "-"
                print(f"  متوسط مسافة SL لباقي صفقات {sym} بنفس الفترة (n={len(other_pcts)}): "
                      f"{avg_other:.3f}%  →  أوسع بـ{ratio_txt}")
            else:
                print(f"  لا توجد صفقات أخرى لـ{sym} بنفس الفترة عندها entry/SL للمقارنة")

            candidates.setdefault(sym, []).append({
                "id": d["id"], "points": d["points"],
                "this_pct": this_pct, "avg_other_pct": avg_other, "ratio": ratio,
            })

        print("\n" + "="*90)
        print("3) قائمة أولويات — رموز مرشّحة لتحليل سقف SL (بالترتيب حسب الأثر)")
        print("="*90)
        priority = []
        for sym, entries in candidates.items():
            total_pts_lost = sum(abs(e["points"]) for e in entries)
            ratios = [e["ratio"] for e in entries if e["ratio"]]
            max_ratio = max(ratios) if ratios else None
            priority.append((sym, len(entries), total_pts_lost, max_ratio))
        priority.sort(key=lambda x: -x[2])

        if not priority:
            print("لا يوجد مرشحون — كل الخسائر الكبيرة كانت إما بالمعادن (معالجة) أو موزّعة بدون تركّز واضح.")
        for rank, (sym, cnt, pts, ratio) in enumerate(priority, 1):
            ratio_txt = f"{ratio:.1f}x أوسع من المعتاد" if ratio else "نسبة غير متاحة (لا صفقات مقارنة)"
            print(f"  {rank}. {sym}: {cnt} صفقة ضمن أعلى 10% خسارة، "
                  f"مجموع نقاط مفقودة={-pts:.2f}، {ratio_txt}")

        print("\n" + "="*90)
        print("4) تحذير حجم العينة")
        print("="*90)
        print(f"   إجمالي القرارات الخاسرة المستخدمة: {len(losing_sorted)}  (أعلى 10% = {top_n} قرار)")
        if top_n < 5:
            print("   ⚠️  عدد قرارات أعلى 10% صغير جداً (<5) — أي استنتاج هون مبدئي فقط،")
            print("       يستاهل تأكيد إضافي قبل أي تعديل فعلي على الكود.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
