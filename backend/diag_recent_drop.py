"""
(2026-10-13) تشخيص للقراءة فقط: أين تركّز تراجع آخر الأيام؟

يقارن القرارات المغلقة بآخر N يوم (حسب الإغلاق، مثل تقرير الداشبورد) مع المرجع
(كل ما قبلها منذ OUTCOME_FIX_DATE)، مقسّمة حسب: الفئة، الرمز، الفريم، الاتجاه،
الجلسة، الثقة، مسافة الوقف %، ويوم الصدور — بنفس verified_unique_decisions (مع دمج المكرر).
ويطبع لكل رمز خاسر: صفقاته واتجاهها ومتى — لكشف "بيع متكرر في سوق صاعد" مثلاً.
لا يكتب شيئاً.

    docker exec moshapi_backend python diag_recent_drop.py [--days 2]
"""
import argparse
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _session(h):
    return "آسيا 00-07" if h < 7 else "لندن 07-12" if h < 12 else "تداخل/نيويورك 12-17" if h < 17 else "نيويورك متأخر 17-24"


def _conf(c):
    c = float(c or 0)
    return "<60" if c < 60 else "60-70" if c < 70 else "70-80" if c < 80 else "80+"


def _slp(s):
    try:
        p = abs(float(s.entry_price) - float(s.stop_loss)) / float(s.entry_price) * 100
    except Exception:
        return "؟"
    return "<0.15%" if p < 0.15 else "0.15-0.3%" if p < 0.3 else "0.3-0.5%" if p < 0.5 else "0.5-1%" if p < 1 else "1%+"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    a = ap.parse_args()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    cut = now - timedelta(days=a.days)
    cat = {r[0].upper(): (r[1] or "?") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}

    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    recent, base = [], []
    for d in verified_unique_decisions(rows):
        s = by_id.get(d["id"])
        if s is None:
            continue
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"])
        if r is None:
            continue
        item = dict(d=d, s=s, r=r)
        (recent if _utc(d["exit_executed"]) and _utc(d["exit_executed"]) >= cut else base).append(item)

    def agg(items):
        n = len(items)
        w = sum(1 for x in items if x["r"] > 0)
        t = sum(x["r"] for x in items)
        return n, w, t

    def show(title, keyf):
        print(f"\n── حسب {title} ── (آخر {a.days} يوم  ‖  المرجع)")
        keys = {}
        for x in recent:
            keys.setdefault(keyf(x), [[], []])[0].append(x)
        for x in base:
            keys.setdefault(keyf(x), [[], []])[1].append(x)
        lines = []
        for k, (rc, bs) in keys.items():
            if not rc:
                continue
            n, w, t = agg(rc)
            bn, bw, bt = agg(bs)
            lines.append((t, f"  {str(k):<22} {n:>3} | نجاح {w / n * 100:4.0f}% | {t:+6.2f}R ({t / n:+.2f})   ‖  "
                             f"{bn:>4} | {bw / bn * 100 if bn else 0:4.0f}% | متوسط {bt / bn if bn else 0:+.2f}R"))
        for _, l in sorted(lines):
            print(l)

    n, w, t = agg(recent)
    bn, bw, bt = agg(base)
    print(f"آخر {a.days} يوم (حسب الإغلاق): {n} قرار | نجاح {w / n * 100 if n else 0:.0f}% | {t:+.2f}R | متوسط {t / n if n else 0:+.2f}R")
    print(f"المرجع منذ {OUTCOME_FIX_DATE:%Y-%m-%d}: {bn} قرار | نجاح {bw / bn * 100:.0f}% | متوسط {bt / bn:+.2f}R")

    show("الفئة", lambda x: cat.get((x["d"]["market"] or "").upper(), "?"))
    show("الرمز", lambda x: x["d"]["market"])
    show("الفريم", lambda x: x["d"]["timeframe"])
    show("الاتجاه", lambda x: x["d"]["signal_type"])
    show("الجلسة (صدور UTC)", lambda x: _session(_utc(x["d"]["created_at"]).hour))
    show("الثقة", lambda x: _conf(x["s"].ai_confidence))
    show("مسافة الوقف", lambda x: _slp(x["s"]))
    show("يوم الصدور", lambda x: _utc(x["d"]["created_at"]).strftime("%a %m-%d"))

    print(f"\n── صفقات الرموز الخاسرة (آخر {a.days} يوم) ──")
    per = {}
    for x in recent:
        per.setdefault(x["d"]["market"], []).append(x)
    for m, xs in sorted(per.items(), key=lambda kv: sum(x["r"] for x in kv[1])):
        if sum(x["r"] for x in xs) >= 0:
            continue
        print(f"  {m}:")
        for x in sorted(xs, key=lambda x: _utc(x["d"]["created_at"])):
            d, s = x["d"], x["s"]
            print(f"     {d['signal_type']:<4} {d['timeframe']:<4} صدرت {_utc(d['created_at']):%m-%d %H:%M} → "
                  f"{d['status']:<8} {x['r']:+.2f}R  ثقة {float(s.ai_confidence or 0):.0f}%  "
                  f"دخول {s.entry_price} وقف {s.stop_loss}")
    db.close()


if __name__ == "__main__":
    main()
