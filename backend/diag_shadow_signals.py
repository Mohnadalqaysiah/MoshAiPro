"""
(2026-10-12) تقرير للقراءة فقط: كيف كانت ستؤدي إشارات الكريبتو التي أوقفناها في العطلة؟

يقرأ shadow_signals (النتائج يملؤها shadow_evaluator آلياً). للمقارنة العادلة مع
diag_crypto_weekend.py:
  - يحاكي قيد النظام الحي "صفقة واحدة مفتوحة لكل (رمز، فريم)": إشارة ظل تُتجاهل إن كانت
    قبلها إشارة مقبولة على نفس الرمز والفريم لم تُغلق بعد.
  - المقياس الأساسي على TP1/TP2/SL فقط (مثل الإحصائيات)، والمنتهية بلا هدف ولا وقف تُعرض منفصلة.

    docker exec moshapi_backend python diag_shadow_signals.py
"""
from datetime import timezone

from app.database import SessionLocal
from app.models.shadow_signal import ShadowSignal


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    rows = db.query(ShadowSignal).order_by(ShadowSignal.created_at).all()
    pending = [s for s in rows if s.outcome is None]
    done = [s for s in rows if s.outcome is not None]

    open_until = {}
    accepted, skipped = [], 0
    for s in done:
        key = (s.market, s.timeframe)
        created = _utc(s.created_at)
        if key in open_until and open_until[key] and open_until[key] > created:
            skipped += 1
            continue
        accepted.append(s)
        open_until[key] = _utc(s.exit_time) or _utc(s.expires_at)

    closed = [s for s in accepted if s.outcome in ("TP1_HIT", "TP2_HIT", "SL_HIT") and s.r_multiple is not None]
    expired = [s for s in accepted if s.outcome in ("EXPIRED_PROFIT", "EXPIRED_LOSS")]
    not_trig = sum(1 for s in accepted if s.outcome == "NOT_TRIGGERED")
    no_data = sum(1 for s in accepted if s.outcome in ("NO_DATA", "EXPIRED_NO_RESULT"))

    print(f"إشارات الظل: {len(rows)} | قُيّمت {len(done)} | بانتظار التقييم {len(pending)}")
    print(f"بعد محاكاة 'صفقة واحدة لكل رمز وفريم': {len(accepted)} (تُجوهلت {skipped})\n")
    if closed:
        rs = [s.r_multiple for s in closed]
        w = sum(1 for r in rs if r > 0)
        print(f"أُغلقت بهدف أو وقف: {len(closed)} | رابحة {w} ({w / len(closed) * 100:.0f}%) | "
              f"مجموع {sum(rs):+.2f}R | متوسط {sum(rs) / len(rs):+.2f}R")
    else:
        print("لا صفقات أُغلقت بهدف أو وقف بعد.")
    if expired:
        er = [s.r_multiple or 0 for s in expired]
        print(f"انتهت مدتها بلا هدف ولا وقف: {len(expired)} | مجموع {sum(er):+.2f}R (منفصلة، لا تدخل المتوسط أعلاه)")
    print(f"لم يتفعّل دخولها: {not_trig} | بلا بيانات: {no_data}")

    print("\nحسب الرمز (المُغلقة بهدف أو وقف):")
    by = {}
    for s in closed:
        by.setdefault(s.market, []).append(s.r_multiple)
    for m, rs in sorted(by.items(), key=lambda kv: sum(kv[1])):
        print(f"  {m:<9} {len(rs):>3} | مجموع {sum(rs):+.2f}R | متوسط {sum(rs) / len(rs):+.2f}R")
    print("\nالمرجع (قبل الإيقاف، 16/09-12/10): كريبتو عطلة −0.25R للصفقة، كريبتو أيام الأسبوع +0.37R.")
    db.close()


if __name__ == "__main__":
    main()
