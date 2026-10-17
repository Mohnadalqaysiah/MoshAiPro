"""
Weekly per-market performance (2026-10-17) — مقياس المالك: الأسبوع × السوق، بمضاعف R (DECISIONS 13/10 "منصة تتعلم"،
الخطوة 2). مشترك بين تبويب الأدمن (GET /admin/weekly-markets) وأداة المراجعة (diag_review.py).

- القرارات الموثّقة الفريدة نفسها التي تستخدمها التقارير (verified_unique_decisions — مع دمج المعاد إصداره).
- الأسبوع = أسبوع **الصدور** (ISO، UTC) — كل صفقة بأسبوع واحد فلا تتداخل الأيام.
- الرابحة = بلغت TP1 (سياسة المالك 16/10). "تأمين" (BREAKEVEN) 0R ويُعدّ منفصلاً خارج نسبة الربح.
- فئة "commodity" بإعدادات الأسواق تجمع المعادن والطاقة والمؤشرات — تُفصل هنا لأن المالك يقيس كل سوق وحده.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

GROUPS = [  # (المفتاح، الاسم)
    ("gold", "الذهب"), ("metals", "الفضة والمعادن"), ("energy", "الطاقة"), ("index", "المؤشرات"),
    ("forex", "فوركس"), ("crypto", "كريبتو"), ("gulf", "خليجي"), ("stock", "أسهم أمريكية"),
]
_GOLD = {"XAUUSD"}
_METALS = {"XAGUSD", "XPTUSD", "XPDUSD", "COPPER"}
_ENERGY = {"USOIL", "OIL", "BRENT", "BRENT OIL", "NATGAS"}
_INDEX = {"NAS100", "US30", "SP500"}
_CLOSED = ("TP1_HIT", "TP2_HIT", "SL_HIT", "BREAKEVEN")


def market_group(symbol: str, category: str) -> str:
    s = (symbol or "").upper()
    if s in _GOLD:
        return "gold"
    if s in _METALS:
        return "metals"
    if s in _ENERGY:
        return "energy"
    if s in _INDEX:
        return "index"
    c = (category or "").lower()
    return c if c in ("forex", "crypto", "gulf", "stock") else ("forex" if c == "commodity" else c or "forex")


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def closed_decisions(db, since: datetime) -> List[Dict]:
    """قرارات مغلقة فريدة منذ since، لكل واحد: created_at، market، group، status، r، side."""
    from app.models.market_config import MarketConfig
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import verified_unique_decisions
    from app.services.quality_report import _r_multiple

    cat = {r[0].upper(): (r[1] or "") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT, SignalStatus.BREAKEVEN]),
        Signal.created_at >= since,
    ).all()
    by_id = {s.id: s for s in rows}
    out = []
    for d in verified_unique_decisions(rows):
        st = getattr(d["status"], "value", d["status"])
        if st not in _CLOSED:
            continue
        s = by_id.get(d["id"])
        if not s:
            continue
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, st)
        if r is None:
            continue
        m = (d["market"] or "").upper()
        out.append({"id": d["id"], "created_at": _utc(d["created_at"]), "market": m,
                    "group": market_group(m, cat.get(m, "")), "status": st, "r": r,
                    "side": getattr(d["signal_type"], "value", d["signal_type"]), "timeframe": d.get("timeframe"),
                    "stop_loss": s.stop_loss, "entry": s.entry_price, "tp2": s.take_profit_2,
                    "premium_discount": s.premium_discount})
    return out


def weekly_table(db, weeks: int = 8) -> Dict:
    from app.services.quality_report import OUTCOME_FIX_DATE
    now = datetime.now(timezone.utc)
    start = now - timedelta(weeks=weeks)
    start = max(start - timedelta(days=start.weekday()), OUTCOME_FIX_DATE)   # من بداية أسبوع ISO
    decs = closed_decisions(db, start.replace(hour=0, minute=0, second=0, microsecond=0))

    def cell():
        return {"n": 0, "wins": 0, "losses": 0, "be": 0, "r": 0.0}

    table: Dict[str, Dict[str, Dict]] = {}
    for d in decs:
        y, w, _ = d["created_at"].isocalendar()
        wk = f"{y}-W{w:02d}"
        row = table.setdefault(wk, {})
        for key in (d["group"], "_total"):
            c = row.setdefault(key, cell())
            if d["status"] == "BREAKEVEN":
                c["be"] += 1
                continue
            c["n"] += 1
            c["wins"] += d["status"] != "SL_HIT"
            c["losses"] += d["status"] == "SL_HIT"
            c["r"] += d["r"]

    week_list = sorted(table)
    out_rows = []
    for wk in week_list:
        row = {}
        for key, c in table[wk].items():
            row[key] = {**c, "r": round(c["r"], 2),
                        "win_rate": round(c["wins"] / c["n"] * 100, 1) if c["n"] else None}
        y, w = int(wk[:4]), int(wk[-2:])
        monday = datetime.fromisocalendar(y, w, 1)
        out_rows.append({"week": wk, "from": monday.date().isoformat(),
                         "to": (monday + timedelta(days=6)).date().isoformat(),
                         "current": monday.date() <= now.date() <= (monday + timedelta(days=6)).date(),
                         "cells": row})
    used = [k for k, _ in GROUPS if any(k in r["cells"] for r in out_rows)]
    summary = {}
    for k in used + ["_total"]:
        cs = [r["cells"][k] for r in out_rows if k in r["cells"] and not r["current"] and r["cells"][k]["n"]]
        summary[k] = {"weeks_won": sum(1 for c in cs if c["r"] > 0), "weeks_lost": sum(1 for c in cs if c["r"] < 0),
                      "total_r": round(sum(c["r"] for c in cs), 2), "n": sum(c["n"] for c in cs)}
    return {"weeks": out_rows, "groups": [{"key": k, "name": dict(GROUPS)[k]} for k in used],
            "summary": summary, "tp1_cap_week": "2026-W42"}
