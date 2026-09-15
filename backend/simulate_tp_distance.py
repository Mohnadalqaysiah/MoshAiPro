"""
simulate_tp_distance.py
==========================
محاكاة قراءة فقط (لا تعديل، لا حفظ) — السؤال الحاسم:
لو كان الهدف الأول أقرب، هل يزيد **الربح** فعلاً أم يزيد عدد الرابحات
فقط بينما يقل الربح؟

الخلفية — خطان مستقلان يلتقيان:
 1) محاكاة "نصف المسافة" السابقة: winrate يقفز 28.4% → 45.7% — لكنها
    حسبت عدد الرابح/الخاسر فقط ولم تحسب النقاط، فتُركت بلا قرار.
 2) تحليل RR (صمد أمام ست مجموعات مختلفة ومقارنة داخل الرمز):
    RR 1.3-1.8 يعطي ~36% winrate ونقاطاً موجبة دائماً، بينما
    RR 1.8-2.5 يعطي ~21% ونقاطاً سالبة دائماً.

كلاهما يقول "الأهداف أبعد من اللازم" — لكن winrate أعلى ≠ ربح أعلى،
لأن الهدف الأقرب يعني ربحاً أصغر بكل صفقة رابحة. هذه المحاكاة تحسم
ذلك بالنقاط الفعلية عبر _calc_points الحيّة نفسها.

المنهج:
 • لكل قرار محسوم: نأخذ الدخول والوقف الحقيقيين كما هما، ونستبدل
   الهدف الأول بهدف عند RR مستهدف (1.3 / 1.5 / 1.8 / 2.0).
 • نمشي على شموع OHLC حقيقية بالترتيب الزمني من لحظة الإنشاء، ونأخذ
   أول مستوى يُلمس (وقف أم هدف).
 • لمس الاثنين داخل نفس الشمعة ⇒ يُحتسب وقفاً (تحفّظ متعمَّد، ونفس
   عُرف _verify_signal_outcome_core بالتطبيق).
 • النقاط تُحسب بنفس دالة _calc_points المستخدمة بالإنتاج.

⚠️ حدود المحاكاة (معلنة صراحة):
 - دقة الشموع 15 دقيقة: لا يمكن ترتيب ما حدث داخل الشمعة الواحدة.
 - لا تُنمذج السبريد ولا الانزلاق ولا رفض التنفيذ.
 - تفترض أن نفس الدخول كان سيُنفَّذ بنفس اللحظة.
 - المقارنة تتم على القرارات القابلة للمحاكاة فقط (نفس المجموعة
   للواقع والمحاكاة) حتى تكون عادلة.

التشغيل:
  docker cp simulate_tp_distance.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/simulate_tp_distance.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.smart_data import smart_data
from app.services.decision_grouping import verified_unique_decisions
from app.api.admin import _calc_points

CUTOFF      = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED      = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
TARGET_RRS  = [1.3, 1.5, 1.8, 2.0]
BAR_TF      = "15m"
MIN_SAMPLE  = 15


async def load_bars(symbol, created_at):
    """شموع حقيقية من لحظة الإنشاء حتى الآن."""
    now = datetime.now(timezone.utc)
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    hours = max(1.0, (now - created).total_seconds() / 3600)
    bars_needed = int(hours * 4) + 20          # 4 شمعات بالساعة على 15m
    bars_needed = min(bars_needed, 5000)
    try:
        df = await smart_data.get_ohlcv(symbol, BAR_TF, bars=bars_needed)
    except Exception:
        return None
    if df is None or len(df) == 0:
        return None
    import pandas as pd
    if "datetime" in df.columns:
        ts = pd.to_datetime(df["datetime"], utc=True)
    else:
        ts = pd.to_datetime(df.index, utc=True)
    rows = [(t, float(h), float(l)) for t, h, l in zip(ts, df["high"], df["low"]) if t >= created]
    rows.sort(key=lambda r: r[0])
    return rows or None


def walk(rows, is_buy, sl, tp):
    """أول مستوى يُلمس زمنياً. تعادل داخل الشمعة ⇒ وقف (تحفّظ)."""
    for _t, hi, lo in rows:
        sl_hit = (lo <= sl) if is_buy else (hi >= sl)
        tp_hit = (hi >= tp) if is_buy else (lo <= tp)
        if sl_hit:
            return "SL"
        if tp_hit:
            return "TP"
    return None


async def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]
        reps = {s.id: s for s in db.query(Signal).filter(
            Signal.id.in_([d["id"] for d in decisions])).all()}

        print(f"قرارات محسومة بالفترة: {len(decisions)} — جاري جلب شموع {BAR_TF} حقيقية "
              f"(قد يستغرق عدة دقائق)...\n")

        sim_rows   = []      # (decision, actual_points, {rr: (outcome, points)})
        skipped    = 0
        for i, d in enumerate(decisions):
            rep = reps.get(d["id"])
            if not rep or not rep.entry_price or not rep.stop_loss:
                skipped += 1
                continue
            entry = float(rep.entry_price)
            sl    = float(rep.stop_loss)
            if entry <= 0 or sl == entry:
                skipped += 1
                continue
            side = rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type
            is_buy = side == "BUY"

            rows = await load_bars(rep.market, rep.created_at)
            await asyncio.sleep(0.25)
            if not rows:
                skipped += 1
                continue

            sl_dist = abs(entry - sl)
            per_rr  = {}
            for rr in TARGET_RRS:
                tp = entry + sl_dist * rr if is_buy else entry - sl_dist * rr
                res = walk(rows, is_buy, sl, tp)
                if res is None:
                    per_rr[rr] = None            # لم يُحسم ضمن البيانات المتاحة
                elif res == "TP":
                    per_rr[rr] = ("TP", _calc_points(rep.market, abs(tp - entry), entry))
                else:
                    per_rr[rr] = ("SL", -_calc_points(rep.market, sl_dist, entry))
            sim_rows.append((d, float(d["points"] or 0), per_rr))

            if (i + 1) % 25 == 0:
                print(f"  … عولج {i+1}/{len(decisions)}")

        print(f"\nقابلة للمحاكاة: {len(sim_rows)}   مستبعدة (لا شموع/لا مستويات): {skipped}\n")
        if not sim_rows:
            return

        # ── الواقع على نفس المجموعة تماماً (مقارنة عادلة) ─────────────────
        act_n    = len(sim_rows)
        act_wins = sum(1 for d, _p, _ in sim_rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
        act_pts  = sum(p for _d, p, _ in sim_rows)
        print("=" * 96)
        print("الواقع الفعلي (نفس مجموعة المقارنة)")
        print("=" * 96)
        print(f"  n={act_n}  رابح={act_wins}  winrate={act_wins/act_n*100:.1f}%  "
              f"نقاط={act_pts:+.2f}  exp={act_pts/act_n:+.2f}")

        print("\n" + "=" * 96)
        print(f"المحاكاة — الهدف الأول عند RR مستهدف (الوقف كما هو)")
        print("=" * 96)
        for rr in TARGET_RRS:
            done = [(d, per[rr]) for d, _p, per in sim_rows if per.get(rr)]
            if not done:
                continue
            n    = len(done)
            wins = sum(1 for _d, (o, _pt) in done if o == "TP")
            pts  = sum(pt for _d, (_o, pt) in done)
            delta = pts - sum(p for d, p, per in sim_rows if per.get(rr))
            print(f"  RR={rr}:  n={n:>3d}  رابح={wins:>3d}  winrate={wins/n*100:>5.1f}%  "
                  f"نقاط={pts:>+9.2f}  exp={pts/n:>+7.2f}   (الفرق عن الواقع: {delta:+.2f})")

        # ── لكل رمز: هل التحسّن عام أم مدفوع برمز واحد؟ ───────────────────
        best_rr = TARGET_RRS[1]
        print("\n" + "=" * 96)
        print(f"التفصيل لكل رمز عند RR={best_rr} — للتأكد أن الأثر ليس مدفوعاً برمز واحد")
        print("=" * 96)
        by_sym = defaultdict(list)
        for d, p, per in sim_rows:
            if per.get(best_rr):
                by_sym[d["market"]].append((d, p, per[best_rr]))
        for sym, rows in sorted(by_sym.items(), key=lambda kv: -len(kv[1])):
            n = len(rows)
            a_w = sum(1 for d, _p, _s in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
            a_p = sum(p for _d, p, _s in rows)
            s_w = sum(1 for _d, _p, (o, _pt) in rows if o == "TP")
            s_p = sum(pt for _d, _p, (_o, pt) in rows)
            flag = "" if n >= MIN_SAMPLE else f"  ⚠️ عينة {n}"
            print(f"  {sym:<12} n={n:>3d} | واقع: {a_w/n*100:>5.1f}% {a_p:>+9.2f}"
                  f" | محاكاة: {s_w/n*100:>5.1f}% {s_p:>+9.2f}"
                  f" | الفرق: {s_p - a_p:>+9.2f}{flag}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
