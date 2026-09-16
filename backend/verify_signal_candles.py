"""
verify_signal_candles.py
===========================
تحقق قراءة فقط من إشارة واحدة مقابل شموع السوق الحقيقية، مع طباعة
الشموع دقيقة-بدقيقة حول وقت الإنشاء — حتى يمكن الحكم بالعين لا بالثقة
بمخرجات الأداة وحدها.

الدافع (16/09): إشارة BTCUSD #2521 ضربت الوقف خلال ~4 دقائق من
إصدارها. سبق بهذه الجلسة أن تبيّن أن إغلاقات سريعة كهذه كانت أحياناً
وهمية بسبب خلل بفلترة زمن الشموع (أُصلح commit c2f6cb8)، وأحياناً
حقيقية تماماً. الفرق يُحسم بالشموع لا بالافتراض.

يطبع أيضاً مسافة الوقف كنسبة — لأن وقفاً بعرض الضجيج يجعل الضرب
السريع نتيجة متوقعة بنيوياً، لا خللاً.

التشغيل:
  docker cp verify_signal_candles.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/verify_signal_candles.py 2521
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone


async def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python verify_signal_candles.py <signal_id>")
        return
    sid = int(sys.argv[1])

    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.smart_data import smart_data
    from app.api.admin import _verify_signal_outcome_core

    db = SessionLocal()
    try:
        s = db.query(Signal).filter(Signal.id == sid).first()
        if not s:
            print(f"لا توجد إشارة #{sid}")
            return

        created = s.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        entry = float(s.entry_price); sl = float(s.stop_loss)
        tp1   = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
        is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
        status = s.status.value if hasattr(s.status, "value") else s.status

        sl_pct = abs(entry - sl) / entry * 100
        tp_pct = abs(tp1 - entry) / entry * 100

        print("=" * 88)
        print(f"إشارة #{sid} — {s.market} / {s.timeframe} / "
              f"{'شراء' if is_buy else 'بيع'}")
        print("=" * 88)
        print(f"  أُنشئت:     {created:%Y-%m-%d %H:%M:%S} UTC")
        print(f"  الدخول:     {entry}")
        print(f"  الوقف:      {sl}   (مسافة {sl_pct:.4f}%)")
        print(f"  الهدف1:     {tp1}   (مسافة {tp_pct:.4f}%)")
        print(f"  RR:         {tp_pct/sl_pct:.2f}   (المسجّل: {s.risk_reward_ratio})")
        print(f"  الحالة:     {status}   النقاط: {s.points_earned}")
        print(f"  أُغلقت:     {s.exit_executed}")

        if sl_pct < 0.15:
            print(f"\n  ⚠️ مسافة الوقف {sl_pct:.4f}% بعرض الضجيج لهذا السوق — "
                  f"ضربها السريع نتيجة متوقعة بنيوياً، لا دليل خلل بحد ذاته.")

        # ── الشموع الحقيقية دقيقة بدقيقة ─────────────────────────────────
        print("\n" + "-" * 88)
        print("الشموع الحقيقية (5 دقائق) من وقت الإنشاء")
        print("-" * 88)
        age_h = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        bars  = max(40, int(age_h * 12) + 12)
        try:
            df = await smart_data.get_ohlcv(s.market, "5m", bars=bars)
        except Exception as e:
            df = None
            print(f"  تعذّر الجلب: {e}")

        if df is not None and len(df):
            import pandas as pd
            # بلا .values — تجريد المنطقة الزمنية يجعل المقارنة ترمي
            # TypeError (نفس العطل المكتشف بحلقة الرصد اليوم).
            work = df.copy()
            ts_col = work["datetime"] if "datetime" in work.columns else work.index
            work["_ts"] = pd.to_datetime(ts_col, utc=True)
            work = work[work["_ts"] >= (created - timedelta(minutes=10))].sort_values("_ts")
            shown = 0
            for _, r in work.iterrows():
                t  = r["_ts"]; hi = float(r["high"]); lo = float(r["low"])
                sl_hit  = (lo <= sl) if is_buy else (hi >= sl)
                tp1_hit = (hi >= tp1) if is_buy else (lo <= tp1)
                mark = "  ⛔ لمست الوقف" if sl_hit else ("  ✅ لمست الهدف1" if tp1_hit else "")
                pre  = " (قبل الإنشاء)" if t < created else ""
                print(f"  {t:%m-%d %H:%M}  high={hi:<12.2f} low={lo:<12.2f}{mark}{pre}")
                shown += 1
                if shown >= 18:
                    break
        else:
            print("  لا توجد شموع متاحة.")

        # ── حكم الأداة المستقلة ──────────────────────────────────────────
        print("\n" + "-" * 88)
        print("حكم أداة التحقق المستقلة (نفس منطق زر 🔍 تحقق)")
        print("-" * 88)
        r = await _verify_signal_outcome_core(s)
        print(f"  النتيجة المكتشفة: {r.get('detected')}")
        print(f"  التفاصيل: {r.get('reason') or r.get('hit_time') or ''}")
        if r.get("detected") and r["detected"] != status:
            print(f"  ⚠️ تختلف عن المسجّل ({status}) — يحتاج تصحيحاً.")
        else:
            print(f"  ✅ تطابق المسجّل ({status}).")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
