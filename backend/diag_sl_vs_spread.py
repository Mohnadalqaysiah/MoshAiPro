"""
diag_sl_vs_spread.py — تشخيص قراءة فقط (2026-10-09)
=====================================================
السؤال: كم من الصفقات الخاسرة كان ستوبها أصغر من أن يتحمّل سبريد الأداة
الحقيقي عند الوسيط؟ (مثال #4361 NATGAS: ستوب 0.0048 وسبريد الغاز 0.003-0.008)

المحرك يقدّر السبريد كـ ATR×0.05 (Rule 9) ويكتفي بتحذير، ولا يوجد حد أدنى
لمسافة الستوب. هذا السكربت يقارن مسافة الستوب بسبريد واقعي لكل أداة
(متوسط وسطاء التجزئة بساعات التداول العادية — تقدير محافظ، لا قياس حي)
ويقسّم القرارات الفريدة لشرائح حسب نسبة الستوب/السبريد، مع نسبة النجاح
ومتوسط R لكل شريحة.

لا يكتب أي شيء.

التشغيل:
  docker cp backend/diag_sl_vs_spread.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_sl_vs_spread.py 2>/dev/null
"""
import sys
sys.path.insert(0, "/app")

from collections import defaultdict
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions

# حلقة الرصد قبل هذا التاريخ معطوبة — لا يُبنى عليها (DECISIONS.md)
TRUSTED_FROM = datetime(2026, 9, 16, tzinfo=timezone.utc)

# سبريد واقعي تقريبي (بوحدة السعر) عند وسطاء التجزئة الشائعين
TYPICAL_SPREAD = {
    "XAUUSD": 0.30, "XAGUSD": 0.03, "XPTUSD": 1.5, "COPPER": 0.003,
    "USOIL": 0.03, "NATGAS": 0.006,
    "BTCUSD": 15.0, "ETHUSD": 1.5, "BNBUSD": 0.5, "SOLUSD": 0.10,
    "XRPUSD": 0.002, "ADAUSD": 0.0008, "DOGEUSD": 0.0003,
    "EURUSD": 0.00010, "GBPUSD": 0.00015, "USDJPY": 0.015, "USDCHF": 0.00015,
    "AUDUSD": 0.00012, "USDCAD": 0.00018, "NZDUSD": 0.00018, "EURGBP": 0.00015,
    "EURJPY": 0.020, "GBPJPY": 0.030, "DXY": 0.03,
    "NAS100": 1.5, "US30": 3.0, "SP500": 0.6,
    "AMD": 0.05, "NFLX": 0.10,
    "USDMYR": 0.0100,
}
# أسهم الخليج: التيك 0.01-0.05 حسب السعر — نعتبر السبريد = تيكين تقريباً
GULF = {"ARAMCO", "RAJHI", "SABIC", "STC", "SNB", "MAADEN", "ALMARAI", "BAHRI",
        "ALINMA", "EMAAR", "EMIRATESNBD", "DIB", "FAB", "ADNOCDIST", "QNBK"}

BUCKETS = [(0, 3, "< 3×"), (3, 5, "3-5×"), (5, 10, "5-10×"), (10, 1e9, "≥ 10×")]


def spread_for(sym: str, entry: float):
    if sym in TYPICAL_SPREAD:
        return TYPICAL_SPREAD[sym]
    if sym in GULF:
        return 0.02 if entry < 10 else 0.04 if entry < 50 else 0.10
    return None


def main():
    db = SessionLocal()
    statuses = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]
    rows = db.query(Signal).filter(Signal.status.in_(statuses),
                                   Signal.created_at >= TRUSTED_FROM).all()
    by_id = {s.id: s for s in rows}
    groups = group_unique_decisions(rows)
    print(f"📊 صفقات محسومة منذ {TRUSTED_FROM.date()}: {len(rows)} صف = {len(groups)} قرار فريد\n")

    agg = {b[2]: {"w": 0, "l": 0, "r": 0.0} for b in BUCKETS}
    per_sym = defaultdict(lambda: {b[2]: [0, 0] for b in BUCKETS})
    unknown = defaultdict(int)
    tight_losses = []

    for g in groups:
        s = by_id[g["id"]]
        sym = (s.market or "").upper()
        entry, sl = float(s.entry_price or 0), float(s.stop_loss or 0)
        risk = abs(entry - sl)
        if not entry or not risk:
            continue
        sp = spread_for(sym, entry)
        if sp is None:
            unknown[sym] += 1
            continue
        ratio = risk / sp
        label = next(b[2] for b in BUCKETS if b[0] <= ratio < b[1])
        st = s.status.value if hasattr(s.status, "value") else s.status
        if st == "SL_HIT":
            r = -1.0
            agg[label]["l"] += 1
            per_sym[sym][label][1] += 1
            if ratio < 3:
                tight_losses.append((s.id, sym, s.timeframe, risk, sp, ratio))
        else:
            tp = float((s.take_profit_2 if st == "TP2_HIT" else s.take_profit_1) or s.take_profit_1)
            r = abs(tp - entry) / risk
            agg[label]["w"] += 1
            per_sym[sym][label][0] += 1
        agg[label]["r"] += r

    print("الشريحة = مسافة الستوب ÷ سبريد الأداة")
    print(f"{'الشريحة':10s} {'قرارات':>7s} {'رابحة':>6s} {'خاسرة':>6s} {'نجاح':>7s} {'متوسط R':>8s} {'مجموع R':>8s}")
    for _, _, label in BUCKETS:
        a = agg[label]; n = a["w"] + a["l"]
        if not n:
            print(f"{label:10s} {0:>7d}"); continue
        print(f"{label:10s} {n:>7d} {a['w']:>6d} {a['l']:>6d} {a['w']*100/n:>6.1f}% {a['r']/n:>+8.2f} {a['r']:>+8.1f}")

    print("\nلكل رمز (رابحة/خاسرة بكل شريحة) — الرموز التي فيها قرارات < 5× فقط:")
    for sym, b in sorted(per_sym.items()):
        if sum(b["< 3×"]) + sum(b["3-5×"]) == 0:
            continue
        cells = "  ".join(f"{lbl}: {w}/{l}" for (_, _, lbl) in BUCKETS for w, l in [b[lbl]])
        print(f"  {sym:12s} {cells}")

    if tight_losses:
        print(f"\nخسائر بستوب أقل من 3× السبريد ({len(tight_losses)}):")
        for sid, sym, tf, risk, sp, ratio in sorted(tight_losses, key=lambda x: x[5])[:40]:
            print(f"  #{sid:5d} {sym:10s} {tf:4s} ستوب={risk:<10.5g} سبريد≈{sp:<8.5g} النسبة={ratio:.1f}×")

    if unknown:
        print(f"\n⚠️ رموز بلا سبريد معروف (مستبعدة): {dict(unknown)}")
    db.close()


if __name__ == "__main__":
    main()
