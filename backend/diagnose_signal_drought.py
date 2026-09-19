"""
diagnose_signal_drought.py
===========================
قراءة محضة — لا يعدّل صفاً ولا يوقف حلقة. يجيب سؤالاً واحداً: صفقة واحدة
فقط 18/09 وصفر اليوم 19/09 (سبت) — هل هذا سكون سوق طبيعي أم عطل بالحلقة؟

اليوم سبت. الفوركس/المعادن/الأسهم مغلقة أصلاً عطلة نهاية الأسبوع — هذا
تفسير بريء متوقَّع. لكن `market_scanner` (app/services/market_scanner.py)
يغطي أيضاً 7 عملات كريبتو تتداول 24/7 (BTCUSD, ETHUSD, BNBUSD, SOLUSD,
XRPUSD, ADAUSD, DOGEUSD) كل 30 دقيقة — فصفر إشارة **بالكريبتو تحديداً**
اليوم لا يفسّره إغلاق السوق، ويستحق تفريقاً بين ثلاثة احتمالات:

  1) الحلقة لا تعمل أصلاً (قفل singleton لم يُحرَز، أو حساب النظام غائب)
  2) الحلقة تعمل وتحلّل لكن لا "توصية" فعلية تخرج (سوق هادئ فعلاً)
  3) الحلقة تعمل وتوصي BUY/SELL لكن الحارس يرفض الحفظ (rejection_reason،
     قفل اتجاه، صفقة نشطة بالفعل على نفس الرمز)

هذا يفرّق بينها بالأرقام لا بالتخمين.

التشغيل:
  docker cp diagnose_signal_drought.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_signal_drought.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone, timedelta
from collections import Counter


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.user import User
    from app.services.smart_data import smart_data as _sd
    from app.services.market_scanner import SCAN_SYMBOLS, SCAN_TIMEFRAMES, SYSTEM_SCANNER_EMAIL

    now = datetime.now(timezone.utc)
    print("=" * 90)
    print(f"تشخيص سكون الإشارات — {now:%Y-%m-%d %H:%M} UTC ({now:%A})")
    print("=" * 90)

    db = SessionLocal()
    try:
        # ── 1) هل حساب الماسح موجود؟ بدونه الحلقة تُرجع فوراً بصمت ─────
        sys_user = db.query(User).filter(User.email == SYSTEM_SCANNER_EMAIL).first()
        print(f"\n[1] حساب الماسح ({SYSTEM_SCANNER_EMAIL}):",
              f"موجود id={sys_user.id}" if sys_user else "❌ غير موجود — الحلقة تتوقف عند أول سطر")

        # ── 2) الإشارات آخر 4 أيام مجمّعة يومياً وبالفئة ────────────────
        since = now - timedelta(days=4)
        rows = (db.query(Signal)
                  .filter(Signal.created_at >= since)
                  .order_by(Signal.created_at.desc()).all())
        by_day = Counter()
        by_day_crypto = Counter()
        crypto_syms = {"BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD"}
        for s in rows:
            c = s.created_at
            if c.tzinfo is None:
                c = c.replace(tzinfo=timezone.utc)
            d = c.strftime("%Y-%m-%d")
            by_day[d] += 1
            if s.market.upper() in crypto_syms:
                by_day_crypto[d] += 1

        print(f"\n[2] عدد الإشارات آخر 4 أيام (الكل / كريبتو فقط):")
        for d in sorted(by_day.keys()):
            print(f"    {d}  →  {by_day[d]:>3}  /  {by_day_crypto.get(d, 0)}")
        if not by_day:
            print("    لا إشارات إطلاقاً بآخر 4 أيام.")

        print(f"\n    آخر 10 إشارات مسجّلة:")
        for s in rows[:10]:
            c = s.created_at
            if c.tzinfo is None:
                c = c.replace(tzinfo=timezone.utc)
            stype = s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type
            print(f"      #{s.id:<6} {s.market:<10} {stype:<5} {c:%m-%d %H:%M} UTC  (user_id={s.user_id})")

        # ── 3) هل السوق مفتوح الآن لكل رمز يغطيه الماسح؟ ────────────────
        print(f"\n[3] حالة السوق الآن لرموز الماسح الآلي ({len(SCAN_SYMBOLS)} رمز):")
        open_syms, closed_syms = [], []
        for sym in SCAN_SYMBOLS:
            try:
                is_open = _sd.is_market_open(sym)
            except Exception as e:
                is_open = None
            (open_syms if is_open else closed_syms).append(sym)
        print(f"    مفتوحة الآن ({len(open_syms)}): {', '.join(open_syms) or '—'}")
        print(f"    مغلقة الآن  ({len(closed_syms)}): {', '.join(closed_syms) or '—'}")

        crypto_open = [s for s in open_syms if s in crypto_syms]
        print(f"\n    كريبتو مفتوحة تحديداً: {', '.join(crypto_open) or '⚠️ ولا واحدة — غير طبيعي، كريبتو 24/7'}")

        # ── الخلاصة ──────────────────────────────────────────────────
        print("\n" + "=" * 90)
        print("الخلاصة")
        print("=" * 90)
        if not sys_user:
            print("  ⛔ الماسح الآلي متوقف كلياً — حساب النظام غير موجود بقاعدة البيانات.")
            print("     التشغيل: docker exec moshapi_backend python /app/migrate_add_system_scanner_user.py")
        elif not crypto_open:
            print("  ⚠️ is_market_open يقول إن كل الكريبتو مغلق الآن — هذا خطأ منطقي")
            print("     (كريبتو لا يغلق)، يستحق فحص smart_data.is_market_open لهذا النوع.")
        else:
            today = now.strftime("%Y-%m-%d")
            yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"  الماسح يعمل والكريبتو مفتوحة. إشارات اليوم={by_day.get(today,0)}"
                  f" (كريبتو={by_day_crypto.get(today,0)}) · أمس={by_day.get(yday,0)}"
                  f" (كريبتو={by_day_crypto.get(yday,0)}).")
            print("  إن كانت إشارات الكريبتو أيضاً صفر رغم فتح السوق وعمل الحساب:")
            print("  السبب على الأرجح لا في التوقّف بل في أن `bot_analyze` يُشغَّل ويُرجع")
            print("  WAIT (لا BUY/SELL) — راجع سطر 'Market scanner cycle done — attempted=…")
            print("  actionable=… errors=…' بسجلات الحاوية:")
            print("     docker logs --since 24h moshapi_backend | grep -i 'market scanner'")
            print("  لو errors مرتفع فهو عطل فعلي؛ لو actionable=0 مع attempted سليم")
            print("  فهو سكون سوق حقيقي (محتمل جداً يوم سبت هادئ) لا عطل.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
