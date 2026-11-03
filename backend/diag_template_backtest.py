"""
(2026-11-03) باكتيست القوالب بشروط القبول المسجّلة (DECISIONS 15/10) — للقراءة فقط، لا يكتب شيئاً ولا يغيّر حالة أي قالب.

"مُختبر" = الأربعة معاً: صافٍ موجب بعد السبريد على 30 و45 يوماً، و20 صفقة فأكثر، وأغلب الأسابيع رابحة، وأقصى تراجع أقل من 6R.
صافٍ سالب على 45 يوماً = "نتائج سلبية". غير ذلك = "قيد الاختبار". الـ30 يوماً تُحسب من صفقات نفس تشغيل الـ45.

    docker exec moshapi_backend python diag_template_backtest.py                      كل القوالب
    docker exec moshapi_backend python diag_template_backtest.py nas_trend_buy ...    قوالب بعينها
"""
import json
import sys
from datetime import datetime, timedelta, timezone

MIN_TRADES = 20
MAX_DD_R = 6.0


def _time(t) -> datetime:
    d = datetime.fromisoformat(str(t["time"]).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def max_drawdown(rs) -> float:
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def judge(trades, now: datetime) -> dict:
    """الشروط الأربعة على صفقات 45 يوماً. r هنا بعد خصم السبريد."""
    trades = sorted(trades, key=_time)
    net45 = sum(t["r"] for t in trades)
    net30 = sum(t["r"] for t in trades if _time(t) >= now - timedelta(days=30))
    weeks = {}
    for t in trades:
        wk = _time(t).isocalendar()[:2]
        weeks[wk] = weeks.get(wk, 0.0) + t["r"]
    won = sum(1 for v in weeks.values() if v > 0)
    dd = max_drawdown([t["r"] for t in trades])
    passed = net45 > 0 and net30 > 0 and len(trades) >= MIN_TRADES and won > len(weeks) / 2 and dd < MAX_DD_R
    status = "tested" if passed else "negative" if net45 < 0 else "testing"
    return {"status": status, "days": 45, "trades": len(trades), "net_r": round(net45, 2), "net_r_30": round(net30, 2),
            "weeks_won": won, "weeks": len(weeks), "max_dd_r": round(dd, 2)}


def main():
    from app.services.strategy_backtest import run_backtest_sync
    from app.services.strategy_templates import all_templates, get_template
    from app.services.template_shadow import template_snapshot

    keys = sys.argv[1:] or [t["key"] for t in all_templates()]
    print(f"{'القالب':<28}{'صفقات':>6}{'صافي 45':>9}{'صافي 30':>9}{'أسابيع':>8}{'تراجع':>7}  الحالة")
    out = {}
    for key in keys:
        t = get_template(key)
        if not t:
            print(f"{key}: غير موجود")
            continue
        res = run_backtest_sync(template_snapshot(t), t["symbols"], 45)
        j = judge(res["trades"], datetime.now(timezone.utc))
        out[key] = j
        print(f"{key:<28}{j['trades']:>6}{j['net_r']:>+9.2f}{j['net_r_30']:>+9.2f}{str(j['weeks_won']) + '/' + str(j['weeks']):>8}"
              f"{j['max_dd_r']:>7.2f}  {j['status']}", flush=True)
    print("\nJSON " + json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
