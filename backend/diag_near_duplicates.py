"""
(2026-10-15) تشخيص للقراءة فقط: صفقات ظهرت مرتين بالتقرير (نفس الرمز والاتجاه وتقريباً نفس الوقت) ولم تُدمج.

بلاغ المالك: XRPUSD 1h شراء 15/10 10:59 مرتين (104 مستخدم + 9 مراقبة)، NAS100 4h شراء 14/10 12:47 مرتين.
لكل زوج قرارين منفصلين بعد الدمج (verified_unique_decisions) صدرا خلال 90 دقيقة على نفس الرمز والاتجاه:
يطبع الصفوف ومستوياتها وأي شرط من شروط "نفس الصفقة" فشل (الدخول ≤0.05%، الوقف ≤25% من المخاطرة،
TP1 ≤25% من مسافة الهدف، والثانية صدرت والأولى مفتوحة). لا يكتب شيئاً.

    docker exec moshapi_backend python diag_near_duplicates.py [أيام=3]
"""
import sys
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import (
    verified_unique_decisions, SAME_TRADE_ENTRY_TOL, SAME_TRADE_LEVEL_TOL,
)

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
WINDOW_MIN = 90


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _v(x):
    return getattr(x, "value", x)


def main():
    db = SessionLocal()
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    rows = db.query(Signal).filter(Signal.created_at >= since).all()
    by_id = {s.id: s for s in rows}
    decs = sorted(verified_unique_decisions(rows), key=lambda d: _utc(d["created_at"]))
    print(f"آخر {DAYS} أيام: {len(rows)} صف ← {len(decs)} قرار فريد\n")

    pairs = 0
    for i, a in enumerate(decs):
        for b in decs[i + 1:]:
            gap = (_utc(b["created_at"]) - _utc(a["created_at"])).total_seconds() / 60
            if gap > WINDOW_MIN:
                break
            if a["market"] != b["market"] or _v(a["signal_type"]) != _v(b["signal_type"]):
                continue
            pairs += 1
            ea, eb = float(a["entry_price"]), float(b["entry_price"])
            sa, sb = float(a["stop_loss"]), float(b["stop_loss"])
            ta, tb = float(a["take_profit_1"]), float(b["take_profit_1"])
            risk, reach = abs(ea - sa), abs(ta - ea)
            entry_pct = abs(eb - ea) / ea
            sl_frac = abs(sb - sa) / risk if risk else 0
            tp_frac = abs(tb - ta) / reach if reach else 0
            a_exit = _utc(a.get("exit_executed")) or _utc(a.get("expires_at"))
            open_ok = a_exit is None or _utc(b["created_at"]) < a_exit
            print("=" * 78)
            print(f"{a['market']} {_v(a['signal_type'])} — بفارق {gap:.0f} دقيقة")
            for tag, d in (("A", a), ("B", b)):
                ids = d.get("row_ids") or [d["id"]]
                srcs = sorted({(by_id[x].user_id, bool(by_id[x].broadcast_sent)) for x in ids if x in by_id})
                print(f"  {tag}: #{d['id']} فريم {d['timeframe']} | صدر {_utc(d['created_at']):%m-%d %H:%M} | "
                      f"دخول {d['entry_price']} وقف {d['stop_loss']} TP1 {d['take_profit_1']} | {_v(d['status'])} | "
                      f"صفوف {len(ids)} | مستخدمون {d.get('user_count')} | (user_id، بث) {srcs[:4]}")
            fails = []
            if entry_pct > SAME_TRADE_ENTRY_TOL:
                fails.append(f"الدخول يختلف {entry_pct * 100:.3f}% (> {SAME_TRADE_ENTRY_TOL * 100:.2f}%)")
            if sl_frac > SAME_TRADE_LEVEL_TOL:
                fails.append(f"الوقف يختلف {sl_frac * 100:.0f}% من المخاطرة (> 25%)")
            if tp_frac > SAME_TRADE_LEVEL_TOL:
                fails.append(f"TP1 يختلف {tp_frac * 100:.0f}% من مسافة الهدف (> 25%)")
            if not open_ok:
                fails.append("الأولى كانت مغلقة/منتهية عند صدور الثانية")
            print("  لماذا لم تُدمج: " + ("؛ ".join(fails) if fails else "كل الشروط تتحقق — ؟ (يُبلَّغ)"))
            print(f"  القياسات: دخول {entry_pct * 100:.3f}% | وقف {sl_frac * 100:.0f}% | TP1 {tp_frac * 100:.0f}% | "
                  f"فريم {a['timeframe']} / {b['timeframe']}")
    print(f"\nأزواج متقاربة لم تُدمج: {pairs}")
    db.close()


if __name__ == "__main__":
    main()
