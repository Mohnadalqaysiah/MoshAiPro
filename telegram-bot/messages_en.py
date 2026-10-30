"""
messages_en.py (2026-10-24) — English versions of the Telegram messages (owner request: users who chose English in their
account receive signals in English). Same function names and signatures as messages.py, so bot.py picks the module by the
user's language: `L = ME if lang == "en" else M`.

Same rules as the Arabic set: R is the main number, masked signals reveal no direction/confidence/levels, expired users get
every result (wins detailed, losses short — no loss is hidden). Market names are the symbol itself (XAUUSD) — the Arabic
names map lives in bot.py and has no English counterpart. news_context is generated in Arabic by the backend, so it is not
shown in English messages (mixed-language lines read as broken).
"""
from datetime import datetime, timezone
from html import escape as _e
from typing import Optional

from messages import fmt_price, r_of, fmt_r, _ts, _bar, _exit_price, outcome_result_r, TeaserGate, CHANNEL_HANDLE  # noqa: F401

DISCLAIMER = "<i>Technical analysis for information only — not investment advice.</i>"
CHANNEL_LINE = f"📢 Our channel: {CHANNEL_HANDLE}"


def ago(iso, now: Optional[datetime] = None) -> str:
    d = _ts(iso)
    if not d:
        return ""
    mins = int(((now or datetime.now(timezone.utc)) - d).total_seconds() // 60)
    if mins < 60:
        m = max(mins, 1)
        return f"{m} min"
    h = mins // 60
    if h < 24:
        return f"{h} h" if mins % 60 < 10 else f"{h} h {mins % 60} min"
    days = h // 24
    return f"{days} day" + ("s" if days != 1 else "")


def _deadline(iso) -> str:
    d = _ts(iso)
    if not d:
        return ""
    return f"⏳ Valid until <b>{d:%H:%M}</b> UTC ({d:%d/%m}) — the setup may change before then"


def _side(stype: str):
    buy = stype == "BUY"
    return buy, ("🟢" if buy else "🔴"), ("BUY" if buy else "SELL")


def signal_full(s: dict, mname: str, tf_label: str, conf: float) -> str:
    buy, dot, side = _side(s.get("signal_type", "BUY"))
    entry, sl, tp1, tp2 = s.get("entry_price"), s.get("stop_loss"), s.get("take_profit_1"), s.get("take_profit_2")
    r1, r2 = r_of(entry, sl, tp1, buy), r_of(entry, sl, tp2, buy)
    tp3 = s.get("take_profit_3")
    mode = {"SWING": "main trend", "SCALP": "quick trade"}.get(s.get("trade_type") or "")
    lines = [
        f"{dot} <b>{side} {_e(mname)}</b>",
        f"<i>{_e(tf_label)}  ·  confidence {conf:.0f}%" + (f"  ·  {mode}" if mode else "") + "</i>",
        "",
        f"▫️ Entry     <code>{fmt_price(entry)}</code>",
        f"🛑 Stop      <code>{fmt_price(sl)}</code>   <i>−1R</i>",
        f"🎯 TP1       <code>{fmt_price(tp1)}</code>   <i>{fmt_r(r1)}</i>",
    ]
    if tp2 and float(tp2) != float(tp1 or 0):
        lines.append(f"{'🎯' if tp3 else '🏁'} TP2       <code>{fmt_price(tp2)}</code>   <i>{fmt_r(r2)}</i>")
    if tp3:
        lines.append(f"🏁 TP3       <code>{fmt_price(tp3)}</code>   <i>{fmt_r(r_of(entry, sl, tp3, buy))}</i>")
    lines += ["", "🛡 At TP1, move your stop to entry to lock the trade."]
    if s.get("expires_at"):
        lines.append(_deadline(s["expires_at"]))
    lines += ["", DISCLAIMER, CHANNEL_LINE]
    return "\n".join(lines)


def signal_masked(s: dict, mname: str, tf_label: str) -> str:
    return "\n".join([
        f"🔒 <b>New signal — {_e(mname)}</b>",
        "",
        f"⏱ Timeframe: {_e(tf_label)}",
        "",
        f"A new signal for Qaffel subscribers is out on {_e(mname)}.",
        "",
        "Full details are for <b>subscribers</b>: direction, entry, stop loss and targets.",
        "",
        "✨ Don't miss the next one. Activate your subscription and get every detail <b>the moment it's issued</b>.",
        "",
        CHANNEL_LINE,
    ])


_HEAD = {"TP3_HIT": "🏆 TP3 hit", "TP2_HIT": "🏆 TP2 hit", "TP1_HIT": "✅ TP1 hit", "BREAKEVEN": "⚖️ Closed at breakeven", "SL_HIT": "🔴 Stop loss hit"}
_TARGET = {"TP1_HIT": "TP1", "TP2_HIT": "TP2", "TP3_HIT": "TP3", "SL_HIT": "Stop", "BREAKEVEN": "Entry"}


def outcome_subscriber(o: dict, mname: str) -> str:
    st = o.get("status")
    _, _, side = _side(o.get("signal_type", "BUY"))
    r = outcome_result_r(o)
    pct = float(o.get("pnl_pct") or 0)
    tip = {"TP3_HIT": "Full target — excellent trade 🎯",
           "TP2_HIT": "Next is TP3 — the stop at entry protects the profit 🛡" if o.get("tp3") else "Full target — excellent trade 🎯",
           "TP1_HIT": "Next is TP2 — the stop at entry protects the profit 🛡",
           "BREAKEVEN": "Breakeven protected your capital — that's its job 🛡",
           "SL_HIT": "The loss was planned in advance (−1R) — sticking to the plan is what wins long term"}.get(st, "")
    lines = [
        f"<b>{_HEAD.get(st, st)} — {_e(mname)}</b>  ·  {side}",
        "",
        f"<b>{fmt_r(r)}</b>   <i>({pct:+.2f}%)</i>",
        f"Entry <code>{fmt_price(o.get('entry'))}</code>  ➜  {_TARGET.get(st, 'Close')} <code>{fmt_price(_exit_price(o))}</code>",
    ]
    if o.get("created_at"):
        lines.append(f"⏱ {ago(o['created_at'])} after the signal")
    if tip:
        lines += ["", f"<i>{tip}</i>"]
    lines.append(CHANNEL_LINE)
    return "\n".join(lines)


def outcome_expired(o: dict, mname: str) -> str:
    st = o.get("status")
    _, _, side = _side(o.get("signal_type", "BUY"))
    r = outcome_result_r(o)
    mkt = _e(o.get("market", "") or mname)
    if st in ("TP1_HIT", "TP2_HIT", "TP3_HIT"):
        target = {"TP3_HIT": "TP3", "TP2_HIT": "TP2"}.get(st, "TP1")
        lines = [
            f"🏆 <b>Qaffel signal result — {target} hit!</b>",
            "",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"🥇 <b>{mkt}  ·  {side}</b>",
            "",
            f"🎯 Entry: <code>{fmt_price(o.get('entry'))}</code>",
            f"🛑 Stop loss: <code>{fmt_price(o.get('sl'))}</code>",
            f"🏆 {target}: <code>{fmt_price(_exit_price(o))}</code>",
            "",
            f"📈 Result: <b>{fmt_r(r).replace('.0R', 'R')}</b> ({float(o.get('pnl_pct') or 0):+.2f}%)",
        ]
        if o.get("created_at"):
            lines += ["", f"⏱ This result came {ago(o['created_at'])} after the signal reached subscribers."]
        lines += [
            "",
            "🔓 Subscribers received the full signal <b>the moment it was issued</b>.",
            "",
            "✨ Renew your subscription to get the next signals <b>before</b> they play out.",
            "",
            CHANNEL_LINE,
        ]
        return "\n".join(lines)
    if st == "BREAKEVEN":
        return f"⚖️ Signal {mkt}  ·  closed at entry — <b>0R</b>"
    return (f"❌ Signal {mkt}  ·  closed at stop loss — <b>−1R</b>\n\n"
            "📊 At Qaffel we show every result as it is — wins and losses, fully transparent.")


def stats_card(st: dict, market_names: Optional[dict] = None) -> str:
    plan_icon = {"trial": "🔵", "weekly": "🟡", "monthly": "🟣"}.get(st.get("plan", ""), "⚪")
    plan_name = {"trial": "Trial", "weekly": "Weekly", "monthly": "Monthly"}.get(st.get("plan", ""), "")
    total, wins, losses = st.get("total_signals", 0), st.get("wins", 0), st.get("losses", 0)
    total_r, avg_r = st.get("total_r"), st.get("avg_r")
    lines = [f"📊 <b>Your stats</b>  ·  {_e(st.get('full_name') or 'User')}"]
    if plan_name:
        lines.append(f"{plan_icon} {plan_name}" + (f"  ·  ends {st['ends_at']}" if st.get("ends_at") else ""))
    lines.append("")
    if not total:
        lines += ["No closed trades yet — your results appear here as soon as the first one closes.", ""]
    else:
        lines += [
            f"<b>{fmt_r(total_r)}</b>  net result" + (f"   <i>(avg {fmt_r(avg_r, 2)} per trade)</i>" if avg_r is not None else ""),
            f"{total} closed  ·  ✅ {wins}  ·  ❌ {losses}  ·  ⏳ {st.get('active_signals', 0)} open",
            f"Win rate {st.get('win_rate', 0):.0f}%   {_bar(st.get('win_rate', 0))}",
        ]
        if st.get("best_r") is not None:
            lines.append(f"🥇 Best {fmt_r(st['best_r'])}   ·   💔 Worst {fmt_r(st.get('worst_r'))}")
        recent = st.get("recent_trades") or []
        if recent:
            lines += ["", "<b>Recent trades</b>"]
            for t in recent[:5]:
                icon = "✅" if t.get("status") in ("TP1_HIT", "TP2_HIT") else "⚖️" if t.get("status") == "BREAKEVEN" else "❌"
                side = "BUY" if t.get("type") == "BUY" else "SELL"
                lines.append(f"{icon} {_e(t.get('market', ''))} {side}  <b>{fmt_r(t.get('r'))}</b>  <i>{_e(t.get('closed_at', ''))}</i>")
        lines.append("")
    wl = st.get("watchlist_filter") or []
    lines.append(f"<i>Based on the {len(wl)} symbols in your watchlist</i>" if wl else "<i>Based on all symbols since you joined</i>")
    lines.append("<i>R = result as a multiple of risk: +1R = you won what you risked, −1R = the stop loss.</i>")
    lines.append(CHANNEL_LINE)
    if st.get("referral_points"):
        lines.append(f"🎁 Referral points: {st['referral_points']}")
    return "\n".join(lines)
