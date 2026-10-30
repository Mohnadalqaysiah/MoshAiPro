"""
(2026-10-30) إصلاح حادثة نشر سلّم الأهداف: صفقات حُفظ لها take_profit_3 من قيمة قديمة بالمحرك (levels["tp3"]) والسلّم معطّل.

معاينة بلا تعديل، و--apply يعيد الهدف الثالث فارغاً فتعود الصفقة بهدفين كما كانت (الهدف الثاني لم يتغير أصلاً).
صف تحقق هدفه "الثالث" القديم لا يُمس ويُعرض للمراجعة، لأن نقاطه ونتيجته حُسبت عليه.

    docker exec moshapi_backend python fix_legacy_tp3.py           # معاينة
    docker exec moshapi_backend python fix_legacy_tp3.py --apply   # تنفيذ
"""
import sys

from sqlalchemy import text

from app.database import SessionLocal


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    rows = db.execute(text(
        "SELECT id, market, timeframe, status, take_profit_2, take_profit_3, tp3_hit_at, broadcast_sent, created_at "
        "FROM signals WHERE take_profit_3 IS NOT NULL ORDER BY id")).fetchall()
    hit = [r for r in rows if r.tp3_hit_at]
    print(f"صفوف بهدف ثالث: {len(rows)} — منها تحقق ثالثها: {len(hit)}\n")
    for r in rows:
        print(f"  #{r.id} {r.market} {r.timeframe} {r.status} TP2={r.take_profit_2} TP3={r.take_profit_3} "
              f"{'⚠️ تحقق' if r.tp3_hit_at else ''} بُثّت={r.broadcast_sent} {r.created_at:%m-%d %H:%M}")
    if not apply:
        print("\nمعاينة فقط — لم يتغير شيء. للتنفيذ أضف --apply")
        db.close()
        return
    n = db.execute(text("UPDATE signals SET take_profit_3 = NULL WHERE take_profit_3 IS NOT NULL AND tp3_hit_at IS NULL")).rowcount
    db.commit()
    db.close()
    print(f"\nتم: أُعيد {n} صفاً إلى هدفين. لم يُمس: {len(hit)}")


if __name__ == "__main__":
    main()
