"""
analyze_gold_rejection_history.py
====================================
تحليل قراءة فقط — التوزيع التاريخي الحقيقي لأسباب رفض الذهب، بدل
لقطة ساعة واحدة من لوقات حاوية أُعيد إنشاؤها للتو.

المصدر: جدول analysis_logs. حقل full_result فيه التحليل كاملاً
(signals.py:138 يخزّن كل المفاتيح) بما فيه rejection_reason و
_pre_reject_levels — أي سجل كامل لكل تحليل ذهب طلبه مستخدم.
⚠️ حدود المصدر بصراحة: تحاليل الماسح التلقائي (bot_analyze، ~144
محاولة ذهب يومياً) لا تُكتب بهذا الجدول — فقط تحاليل المستخدمين عبر
الموقع. فالعيّنة هنا أصغر من الواقع لكنها تاريخية وحقيقية.

يجيب على ثلاثة أسئلة:
  1) ما توزيع أسباب رفض الذهب عبر الأيام الماضية؟
  2) للمرفوضة بسبب السقف: كم كانت مسافة SL المقصودة مقابل السقف؟
  3) الإشارات اللي نجحت فعلاً تاريخياً — كم كانت مسافة وقفها؟
     (لو المسافات اللي مرّت تاريخياً ضيقة والمحرك اليوم يطلب أوسع
      بكثير، فالتغيّر ببنية السوق أو بتوليد المستويات، لا بالسقف.)

التشغيل:
  docker cp analyze_gold_rejection_history.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_gold_rejection_history.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from app.database import SessionLocal
from app.models.analysis_log import AnalysisLog
from app.models.signal import Signal

SYMBOL     = "XAUUSD"
DAYS       = 21
CONTROL    = "XAGUSD"   # الضابط: ينتج إشارات فعلاً


def sl_stats(full):
    """يرجّع (sl_pct, cap_pct, atr) من نتيجة تحليل محفوظة، أو (None,None,None)."""
    if not isinstance(full, dict):
        return None, None, None
    levels = full.get("levels") or {}
    if not levels.get("stop_loss"):
        levels = full.get("_pre_reject_levels") or {}
    entry = levels.get("entry")
    sl    = levels.get("stop_loss")
    atr   = levels.get("atr")
    try:
        entry, sl = float(entry), float(sl)
        if entry <= 0:
            return None, None, None
        sl_pct = abs(entry - sl) / entry
        atr_f  = float(atr or 0)
        cap    = max(0.005, atr_f / entry) if atr_f > 0 else 0.005
        return sl_pct, cap, atr_f
    except (TypeError, ValueError):
        return None, None, None


def section(db, symbol, cutoff):
    print("\n" + "=" * 100)
    print(f"{symbol} — تحاليل محفوظة بـanalysis_logs آخر {DAYS} يوم")
    print("=" * 100)

    logs = (db.query(AnalysisLog)
              .filter(AnalysisLog.market == symbol, AnalysisLog.created_at >= cutoff)
              .order_by(AnalysisLog.created_at.asc()).all())
    if not logs:
        print("  ⚠️ لا توجد أي تحاليل محفوظة لهذا الرمز بهذه الفترة.")
        return

    recs    = Counter()
    reasons = Counter()
    by_tf   = defaultdict(Counter)
    cap_blocked = []

    for lg in logs:
        full = lg.full_result or {}
        rec  = lg.recommendation or full.get("recommendation") or "?"
        recs[rec] += 1
        reason = (full.get("rejection_reason") or "").strip()
        if reason:
            reasons[reason] += 1
            by_tf[lg.timeframe][reason] += 1
        sl_pct, cap, atr = sl_stats(full)
        if sl_pct is not None and cap is not None and sl_pct > cap:
            cap_blocked.append((lg.created_at, lg.timeframe, sl_pct, cap, atr, reason or rec))

    print(f"  إجمالي التحاليل: {len(logs)}")
    print(f"  التوصيات: " + ", ".join(f"{k}={v}" for k, v in recs.most_common()))

    print(f"\n  أسباب الرفض المسجّلة ({sum(reasons.values())} من {len(logs)}):")
    if not reasons:
        print("    (لا يوجد أي رفض مسجّل)")
    for reason, n in reasons.most_common():
        print(f"    {n:4d}×  {reason}")

    if by_tf:
        print("\n  حسب الفريم:")
        for tf, c in sorted(by_tf.items()):
            print(f"    {tf:5s}: " + ", ".join(f"{r}={n}" for r, n in c.most_common(3)))

    print(f"\n  تحاليل مسافة وقفها تتجاوز سقف ATR فعلياً ({len(cap_blocked)} من {len(logs)}):")
    if not cap_blocked:
        print("    لا شيء — السقف لم يكن قيداً بأي تحليل محفوظ.")
    for ts, tf, sl_pct, cap, atr, why in cap_blocked[-15:]:
        print(f"    {ts:%m-%d %H:%M} {tf:4s} وقف={sl_pct*100:6.3f}%  سقف={cap*100:6.3f}%  "
              f"ATR={atr:8.3f}  ({why})")


def main():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
        section(db, SYMBOL, cutoff)
        section(db, CONTROL, cutoff)

        # ── الإشارات اللي نجحت فعلاً: كم كانت مسافة وقفها؟ ────────────────
        print("\n" + "=" * 100)
        print(f"{SYMBOL} — الإشارات اللي مرّت فعلاً وانحفظت (كل التاريخ)")
        print("=" * 100)
        rows = (db.query(Signal)
                  .filter(Signal.market == SYMBOL)
                  .order_by(Signal.created_at.desc()).limit(40).all())
        if not rows:
            print("  لا توجد.")
        seen = set()
        for s in rows:
            key = (s.timeframe, float(s.entry_price or 0), s.created_at.replace(second=0, microsecond=0))
            if key in seen:
                continue   # صفوف مكررة لكل مستخدم — قرار واحد
            seen.add(key)
            try:
                sl_pct = abs(float(s.entry_price) - float(s.stop_loss)) / float(s.entry_price) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            status = s.status.value if hasattr(s.status, "value") else s.status
            print(f"  #{s.id:5d} {s.timeframe:5s} وقف={sl_pct:6.3f}%  {status:9s} "
                  f"نقاط={s.points_earned if s.points_earned is not None else 0:+8.2f}  {s.created_at:%Y-%m-%d %H:%M}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
