"""
fix_outcomes_pass2.py — التصحيح الثاني لنتائج الرصد (2026-10-10)
=================================================================
يُشغَّل **بعد** fix_pre_entry_outcomes.py --apply (يبني على حالاته المصحَّحة)،
ويستخدم نفس دالة المشي ونفس مصادر الشموع منه حرفياً.

خللان أُصلحا بـbot.py اليوم، وهذا يصحّح أثرهما على التاريخ منذ 2026-09-24:

(أ) TP2 ضائع: تسجيل TP1 كان يُخرج الصفقة من الرصد، فأي TP2 بعده لا يُسجَّل.
    يُرقّى TP1_HIT → TP2_HIT إذا:
      1) شمعة التفعيل تطابق entry_executed (±10 دقائق)
      2) المشي الصحيح بعد الدخول يبلغ TP2 قبل الستوب وضمن مدة الإشارة

(ب) حكم بسعر لحظي من غير مرجع المستويات: لغير الذهب والفضة كان السعر
    اللحظي يُقرأ من TV بينما المستويات مبنية على get_ohlcv (US30/SP500
    آجلة مقابل نقدي بـTV). يُصحَّح الصف إذا:
      1) شمعة التفعيل تطابق entry_executed (±10 دقائق)
      2) المشي الصحيح يعطي نتيجة غير المسجّلة
      3) السعر الذي سجّلته الحلقة عند الإغلاق (current_price) **غير موجود**
         بشموع المرجع حول لحظة الإغلاق (±10 دقائق) — أي أن الحكم صدر بسعر لم
         يوجد بالمرجع الذي بُنيت عليه المستويات
    (لا ينطبق على الذهب والفضة — مرجعهما TV أصلاً.)

ما لا يحقق شروطه يُعرض "غير مؤكَّد" ولا يُلمس. لا notes، لا إشعارات.
⚠️ DRY-RUN افتراضياً. التطبيق بـ--apply صراحة.

التشغيل:
  docker cp backend/fix_outcomes_pass2.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_outcomes_pass2.py 2>/dev/null
  docker exec moshapi_backend python /app/fix_outcomes_pass2.py --apply 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")

from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.api.admin import _calc_points
from fix_pre_entry_outcomes import walk, _tv_candles, _yf_candles, _aware, SPOT_TV, BUG_SINCE, ALIGN_TOL

APPLY = "--apply" in sys.argv
PX_TOL = timedelta(minutes=10)
WIN = ("TP1_HIT", "TP2_HIT")


def _apply(s, truth, entry, sl, tp1, tp2, is_buy, xts):
    if truth == "EXPIRED":
        s.status = SignalStatus.EXPIRED
        s.points_earned = None
        s.profit_loss = 0.0
        s.profit_loss_percentage = 0.0
        s.current_price = None
        s.exit_executed = None
    else:
        exit_p = sl if truth == "SL_HIT" else tp2 if truth == "TP2_HIT" else tp1
        pts = _calc_points(s.market, abs(exit_p - entry), entry)
        if truth == "SL_HIT":
            pts = -pts
        pct = ((exit_p - entry) if is_buy else (entry - exit_p)) / entry * 100
        s.status = SignalStatus(truth)
        s.points_earned = round(pts, 2)
        s.profit_loss = round(pts, 2)
        s.profit_loss_percentage = round(pct, 3)
        s.current_price = exit_p
        s.exit_executed = xts.to_pydatetime() if hasattr(xts, "to_pydatetime") else xts
    s.outcome_verified = True


async def main():
    db = SessionLocal()
    try:
        rows = (db.query(Signal)
                .filter(Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
                        Signal.created_at >= BUG_SINCE,
                        Signal.entry_executed.isnot(None))
                .order_by(Signal.market, Signal.id).all())
        print(f"📊 صفوف محسومة منذ {BUG_SINCE.date()} بدخول مسجَّل: {len(rows)}  —  "
              f"{'تطبيق فعلي' if APPLY else 'معاينة فقط (DRY-RUN)'}\n")

        by_market = defaultdict(list)
        for s in rows:
            by_market[s.market.upper()].append(s)

        now = datetime.now(timezone.utc)
        fixes, uncertain = [], []
        no_data = Counter()
        consistent = 0

        for mk, sigs in sorted(by_market.items()):
            try:
                df = await _tv_candles(mk) if mk in SPOT_TV else \
                     await asyncio.get_event_loop().run_in_executor(None, _yf_candles, mk)
            except Exception as e:
                df = None
                print(f"  ⚠️ {mk}: فشل جلب الشموع: {type(e).__name__}: {e}")
            if df is None or not len(df):
                no_data[mk] += len(sigs)
                continue
            df = df.sort_values("ts")
            data = list(zip(df.ts, df.high.astype(float), df.low.astype(float)))
            first_ts, last_ts = df.ts.iloc[0], df.ts.iloc[-1]
            await asyncio.sleep(1.0)

            for s in sigs:
                created = _aware(s.created_at)
                exp = _aware(s.expires_at) or (created + timedelta(hours=72))
                end = min(exp, now)
                if first_ts > created - timedelta(seconds=60):
                    no_data[mk] += 1
                    continue
                entry, sl = float(s.entry_price), float(s.stop_loss)
                tp1 = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
                is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
                rec = s.status.value if hasattr(s.status, "value") else s.status

                st, ets, xts, _pre = walk(data, created, end, entry, sl, tp1, tp2, is_buy)
                if st is None and (last_ts < end or exp > now):
                    no_data[mk] += 1          # لا تغطية كاملة أو لسا ضمن مدتها — لا حكم
                    continue
                truth = st or "EXPIRED"
                if truth == rec:
                    consistent += 1
                    continue

                ee = _aware(s.entry_executed)
                aligned = ets is not None and abs(ets - ee) <= ALIGN_TOL
                item = dict(s=s, mk=mk, rec=rec, truth=truth, ets=ets, xts=xts,
                            entry=entry, sl=sl, tp1=tp1, tp2=tp2, is_buy=is_buy)

                # (أ) ترقية TP1 → TP2
                if rec == "TP1_HIT" and truth == "TP2_HIT":
                    if aligned:
                        fixes.append({**item, "kind": "أ: TP2 ضائع → ترقية"})
                    else:
                        uncertain.append({**item, "why": "تفعيل الشموع لا يطابق المسجّل"})
                    continue

                # (ب) حكم بسعر لحظي من غير المرجع
                why = []
                if mk in SPOT_TV:
                    why.append("ذهب/فضة — مرجعهما TV أصلاً، ليس هذا الخلل")
                if not aligned:
                    why.append("تفعيل الشموع لا يطابق المسجّل")
                px, xe = s.current_price, _aware(s.exit_executed)
                if px is None or xe is None:
                    why.append("لا سعر/وقت إغلاق مسجّل")
                else:
                    seg = df[(df.ts >= xe - PX_TOL - timedelta(minutes=5)) & (df.ts <= xe + PX_TOL)]
                    if not len(seg):
                        why.append("لا شموع حول لحظة الإغلاق")
                    else:
                        lo_, hi_ = float(seg.low.min()), float(seg.high.max())
                        if lo_ <= float(px) <= hi_:
                            why.append(f"سعر الإغلاق المسجّل {px:.6g} موجود بالمرجع [{lo_:.6g}–{hi_:.6g}]")
                        else:
                            item["px_proof"] = f"سعر الإغلاق المسجّل {px:.6g} خارج المرجع [{lo_:.6g}–{hi_:.6g}]"
                if why:
                    uncertain.append({**item, "why": " · ".join(why)})
                else:
                    kind = ("ب: ربح وهمي → خسارة" if rec in WIN and truth == "SL_HIT" else
                            "ب: خسارة وهمية → ربح" if rec == "SL_HIT" and truth in WIN else
                            "ب: → انتهت بلا نتيجة" if truth == "EXPIRED" else "ب: تعديل مستوى الهدف")
                    fixes.append({**item, "kind": kind})

        kinds = Counter()
        print("✅ تصحيحات مؤكَّدة:")
        for it in fixes:
            s = it["s"]
            kinds[it["kind"]] += 1
            print(f"  #{s.id:5d} {it['mk']:10s} {s.timeframe:4s} {'BUY ' if it['is_buy'] else 'SELL'}  "
                  f"{it['rec']:8s} → {it['truth']:8s}  [{it['kind']}]"
                  + (f"  حسم {it['xts']:%m-%d %H:%M}" if it["xts"] is not None else "")
                  + (f"  — {it['px_proof']}" if it.get("px_proof") else ""))

        if uncertain:
            print(f"\n⚠️ فروق غير مؤكَّدة — لن تُلمس ({len(uncertain)}):")
            for it in uncertain:
                print(f"  #{it['s'].id:5d} {it['mk']:10s} {it['rec']:8s} ≠ شموع {it['truth']:8s}  — {it['why']}")

        if APPLY:
            for it in fixes:
                _apply(it["s"], it["truth"], it["entry"], it["sl"], it["tp1"], it["tp2"], it["is_buy"], it["xts"])
            db.commit()

        print("\n" + "=" * 90)
        print(f"متطابقة مع الشموع: {consistent}   تصحيحات مؤكَّدة: {len(fixes)}   "
              f"غير مؤكَّدة (لم تُلمس): {len(uncertain)}   بلا حكم (تغطية/ضمن المدة): {sum(no_data.values())}")
        for k, v in sorted(kinds.items()):
            print(f"   {k}: {v}")
        print("=" * 90)
        print("✅ تم التطبيق." if APPLY else "ℹ️ معاينة فقط — لم يُكتب شيء. للتطبيق: --apply")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
