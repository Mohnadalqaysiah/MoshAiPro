"""
(2026-10-12) تشخيص للقراءة فقط: هل إشارات الكريبتو في عطلة نهاية الأسبوع أضعف؟

القاعدة مسجّلة في DECISIONS.md (2026-10-12) **قبل** تشغيل هذا الفحص، ولا تُعدَّل بعد رؤية الأرقام:
  العطلة = السبت والأحد UTC حسب وقت صدور الإشارة؛ البيانات منذ OUTCOME_FIX_DATE؛ قرارات فريدة موثّقة.
  إن بلغت قرارات الكريبتو بالعطلة ≥ 30 و متوسطها أسوأ من −0.2R ← تُوقف بالعطلة في مراجعة 2026-10-17.

يطبع للمقارنة: كريبتو عطلة / كريبتو أيام الأسبوع / باقي الرموز، ثم حكم القاعدة آلياً.
لا يكتب شيئاً بقاعدة البيانات.

    docker exec moshapi_backend python diag_crypto_weekend.py
"""
import math
from datetime import timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

MIN_N = 30          # من القاعدة المسجّلة — لا تُعدَّل
MAX_AVG_R = -0.2    # من القاعدة المسجّلة — لا تُعدَّل


def _utc(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _stats(rs):
    n = len(rs)
    if not n:
        return n, 0, 0.0, 0.0, None
    wins = sum(1 for r in rs if r > 0)
    tot = sum(rs)
    avg = tot / n
    if n > 1:
        sd = math.sqrt(sum((r - avg) ** 2 for r in rs) / (n - 1))
        ci = 1.96 * sd / math.sqrt(n)
    else:
        ci = None
    return n, wins, tot, avg, ci


def _line(name, rs):
    n, w, tot, avg, ci = _stats(rs)
    if not n:
        return f"{name:<24} لا قرارات"
    ci_txt = f"  (نطاق 95%: {avg - ci:+.2f} إلى {avg + ci:+.2f})" if ci is not None else ""
    return f"{name:<24} {n:>4} قرار | رابحة {w:>3} ({w / n * 100:4.0f}%) | مجموع {tot:+7.2f}R | متوسط {avg:+.2f}R{ci_txt}"


def main():
    db = SessionLocal()
    crypto = {r[0].upper() for r in db.query(MarketConfig.symbol).filter(MarketConfig.category == "crypto").all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}

    groups = {"cw": [], "cd": [], "ow": [], "od": []}
    per_symbol = {}
    for d in verified_unique_decisions(rows):
        rep = by_id.get(d["id"])
        if rep is None:
            continue
        r = _r_multiple(rep.entry_price, rep.stop_loss, rep.take_profit_1, rep.take_profit_2, d["status"])
        if r is None:
            continue
        is_c = (d["market"] or "").upper() in crypto
        wkend = _utc(d["created_at"]).weekday() >= 5
        groups[("c" if is_c else "o") + ("w" if wkend else "d")].append(r)
        if is_c and wkend:
            per_symbol.setdefault(d["market"], []).append(r)

    print(f"البيانات منذ {OUTCOME_FIX_DATE:%Y-%m-%d} | رموز الكريبتو: {len(crypto)}\n")
    print(_line("كريبتو — عطلة", groups["cw"]))
    print(_line("كريبتو — أيام الأسبوع", groups["cd"]))
    print(_line("غير الكريبتو — عطلة", groups["ow"]))
    print(_line("غير الكريبتو — أيام الأسبوع", groups["od"]))

    print("\nكريبتو العطلة حسب الرمز:")
    for sym, rs in sorted(per_symbol.items(), key=lambda kv: sum(kv[1])):
        print("  " + _line(sym, rs))

    n, _, _, avg, _ = _stats(groups["cw"])
    print("\n── حكم القاعدة المسجّلة مسبقاً ──")
    print(f"الشرط 1: عدد قرارات كريبتو العطلة ≥ {MIN_N} ← {n} ← {'✅ متحقق' if n >= MIN_N else '❌ غير متحقق'}")
    print(f"الشرط 2: المتوسط أسوأ من {MAX_AVG_R}R ← {avg:+.2f}R ← {'✅ متحقق' if n and avg < MAX_AVG_R else '❌ غير متحقق'}")
    if n >= MIN_N and avg < MAX_AVG_R:
        print("النتيجة: الشرطان متحققان ← إيقاف إشارات الكريبتو بالعطلة في مراجعة 2026-10-17.")
    else:
        print("النتيجة: لا يتحقق الشرطان ← تبقى كما هي، ويُعاد القياس بعد أسبوعين.")
    db.close()


if __name__ == "__main__":
    main()
