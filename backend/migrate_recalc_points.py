"""
migrate_recalc_points.py
========================
يُعيد حساب points_earned لجميع الإشارات المغلقة (TP1/TP2/SL)
باستخدام المعادلة الصحيحة الموحّدة:
  - XAUUSD / XAGUSD / Metals : price_diff × 100
  - BTCUSD / ETHUSD          : price_diff × 1
  - JPY pairs                : price_diff × 100
  - Forex (default)          : price_diff × 10000

المشكلة التي تُصحَّح:
  XAGUSD كان يستخدم ×10000 بدل ×100 → قسمة على 100 للنقاط القديمة

التشغيل:
  docker cp migrate_recalc_points.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_recalc_points.py
"""
import sys, os
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus


# ── نفس المعادلة من admin.py ──────────────────────────────────────────────
def _calc_points(market: str, price_diff: float) -> float:
    symbol = (market or "").upper()
    if symbol in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"):
        return round(price_diff * 100, 2)
    elif symbol in ("BTCUSD", "ETHUSD", "BNBUSD"):
        return round(price_diff * 1.0, 2)
    elif symbol.endswith("JPY"):
        return round(price_diff * 100, 2)
    else:
        return round(price_diff * 10000, 2)


def recalc():
    db = SessionLocal()
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    signals = db.query(Signal).filter(Signal.status.in_(closed)).all()
    print(f"📊 Found {len(signals)} closed signals to recalculate")

    updated = skipped = errors = 0

    for s in signals:
        try:
            entry = s.entry_price
            sl    = s.stop_loss
            tp1   = s.take_profit_1
            tp2   = s.take_profit_2

            if not entry:
                skipped += 1
                continue

            status = s.status.value if hasattr(s.status, 'value') else str(s.status)

            if status == "TP1_HIT":
                diff   = abs((tp1 or entry) - entry)
                points = _calc_points(s.market, diff)

            elif status == "TP2_HIT":
                diff   = abs((tp2 or tp1 or entry) - entry)
                points = _calc_points(s.market, diff)

            elif status == "SL_HIT":
                diff   = abs((sl or entry) - entry)
                points = -_calc_points(s.market, diff)

            else:
                skipped += 1
                continue

            old_pts = s.points_earned or 0
            s.points_earned = points
            s.profit_loss   = points

            print(f"  Signal #{s.id:4d}  {s.market or '?':8s}  {status:8s}  "
                  f"old={old_pts:>10.2f}  new={points:>10.2f}  "
                  f"{'✅ CHANGED' if abs(old_pts - points) > 0.01 else '— same'}")
            updated += 1

        except Exception as e:
            print(f"  ⚠️  Signal #{s.id} error: {e}")
            errors += 1

    db.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f"✅ Done: {updated} recalculated, {skipped} skipped, {errors} errors")
    print(f"{'='*60}")


if __name__ == "__main__":
    recalc()
