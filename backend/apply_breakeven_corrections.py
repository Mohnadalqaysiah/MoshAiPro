"""
(2026-10-16، قرار المالك) تحويل الصفقات التي وصلتها رسالة التأمين ثم سُجّلت خاسرة (SL_HIT) إلى "تأمين" (BREAKEVEN، 0R).

نفس اختيار diag_breakeven_losses.py: قرار فريد (verified_unique_decisions) أي صف منه be_alert_sent=True وحالته SL_HIT.
يُحوَّل كل صف SL_HIT بالقرار (كل المشتركين) — النقاط والربح = 0. لا يرسل أي إشعار. افتراضياً DRY-RUN.

    docker exec moshapi_backend python apply_breakeven_corrections.py            # معاينة
    docker exec moshapi_backend python apply_breakeven_corrections.py --apply    # تنفيذ
"""
import sys
from datetime import timezone

from loguru import logger
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import OUTCOME_FIX_DATE


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    n_dec = n_rows = 0
    for d in verified_unique_decisions(rows):
        if d["status"] != "SL_HIT":
            continue
        ids = [i for i in (d.get("row_ids") or [d["id"]]) + (d.get("merged_row_ids") or []) if i in by_id]
        if not any(by_id[i].be_alert_sent for i in ids):
            continue
        n_dec += 1
        targets = [by_id[i] for i in ids if by_id[i].status == SignalStatus.SL_HIT]
        n_rows += len(targets)
        print(f"#{d['id']:<5} {d['market']:<10} {d['timeframe']:<4} {d['signal_type']:<4} "
              f"{d['created_at']:%m-%d %H:%M} — {len(targets)} صف SL_HIT → BREAKEVEN")
        if apply:
            for s in targets:
                s.status = SignalStatus.BREAKEVEN
                s.points_earned = 0.0
                s.profit_loss = 0.0
                s.profit_loss_percentage = 0.0
                logger.info(f"[BE-FIX] #{s.id} {s.market} SL_HIT -> BREAKEVEN")
    if apply:
        db.commit()
    print(f"\n📊 قرارات: {n_dec} | صفوف: {n_rows}")
    print("✅ تم التطبيق." if apply else "ℹ️ dry-run — لم يُعدَّل شيء. شغّل بـ--apply للتنفيذ.")
    db.close()


if __name__ == "__main__":
    main()
