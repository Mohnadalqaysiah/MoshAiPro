"""
(2026-11-12) "الإعداد الموصى به" للعميل — قرار المالك "طبقه وبدي يبقى بالمنصة وفيه نصيحة مرتبه".
(2026-11-14) صار **باقات تخصص** — قرار المالك "نفذ" بعد diag_client_experience: المنصة رابحة لمن يأخذ كل الإشارات
(88% أيام موجبة) لكن "الكل" ≈ 20 إشارة/يوم ولا إنسان ينفّذها؛ الذهب+المعادن ≈ 3/يوم بأعلى متوسط وأخف أسوأ يوم. DECISIONS.md 14/11.

مصدر واحد: الموقع (/auth/preferences/presets و/recommended) والبوت (/bot/presets و/bot/apply-recommended).
- كل باقة: كل الفريمات، بلا حد ثقة، الإشعارات مفعّلة؛ تختلف بالأسواق فقط.
- أرقام كل باقة **تُحسب حياً** من آخر WINDOW_DAYS يوماً (لا تُكتب ثابتة بالنص)، بلا الأسهم الأمريكية الموقوفة، بكاش ساعة.
- لا يُطبَّق على أحد تلقائياً — فقط من يضغط.
"""
import time
from datetime import datetime, timedelta, timezone

# (المفتاح، مجموعات weekly_markets.market_group أو None = الكل)
PRESETS = [
    ("metals", {"gold", "metals"}),
    ("crypto", {"crypto"}),
    ("all", None),
]
RECOMMENDED_PRESET = "metals"          # الموصى به لأغلب العملاء (عدد يُتابَع + أخف أسوأ يوم)
PRESET_KEYS = [k for k, _ in PRESETS]
WINDOW_DAYS = 30
_CACHE_TTL = 3600
_cache = {"at": 0.0, "stats": None}


def preset_symbols(db):
    """{مفتاح: [رموز نشطة]} — "all" = [] (القائمة الفارغة = كل الأسواق، اتفاقية البث)."""
    from app.models.market_config import MarketConfig
    from app.services.weekly_markets import market_group
    rows = db.query(MarketConfig.symbol, MarketConfig.category).filter(MarketConfig.is_active == True).all()  # noqa: E712
    out = {}
    for key, groups in PRESETS:
        out[key] = [] if groups is None else sorted(s.upper() for s, c in rows if market_group(s, c or "") in groups)
    return out


def current_preset(user, syms):
    """أي باقة يطابقها إعداد العميل المحفوظ (أسواقه فقط)، أو "custom"."""
    wl = {s.upper() for s in (user.notify_watchlist or [])}
    for key, _ in PRESETS:
        if wl == set(syms.get(key) or []):
            return key
    return "custom"


def deviations(user) -> list[str]:
    """ما يحجب عن العميل إشارات داخل باقته: timeframes / confidence / notifications (الأسواق اختيار لا انحراف)."""
    out = []
    if [t for t in (user.notify_timeframes or []) if t != "all"]:
        out.append("timeframes")
    if user.notify_min_confidence:
        out.append("confidence")
    if user.notifications_enabled is False:
        out.append("notifications")
    return out


def apply(user, symbols) -> None:
    """يضبط العميل على باقة (بلا commit — المستدعي يحفظ)."""
    user.notify_watchlist = list(symbols)
    user.notify_timeframes = []
    user.notify_min_confidence = 0
    user.notifications_enabled = True


def compute_stats(decs, syms, days):
    """لكل باقة: عدد/يوم، النجاح، الأيام الرابحة، أسوأ يوم — من قرارات محسومة (بلا تعادل وبلا أسهم)."""
    from app.services.client_experience import experience
    out = {}
    for key, groups in PRESETS:
        ds = decs if groups is None else [d for d in decs if d["group"] in groups]
        e = experience(ds, days)
        out[key] = None if e is None else {
            "n": e["n"], "per_day": round(e["per_day"], 1), "win": round(e["win"]), "pos_days": round(e["pos_days"]),
            "worst_day_r": round(e["worst_day"], 1), "symbols": len(syms.get(key) or []),
        }
    return out


def preset_stats(db):
    """أرقام الباقات الحية (كاش ساعة)."""
    now = time.time()
    if _cache["stats"] is not None and now - _cache["at"] < _CACHE_TTL:
        return _cache["stats"]
    from app.services.weekly_markets import closed_decisions
    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    decs = sorted((d for d in closed_decisions(db, since) if d["status"] != "BREAKEVEN" and d["group"] != "stock"),
                  key=lambda d: d["created_at"])
    stats = compute_stats(decs, preset_symbols(db), WINDOW_DAYS)
    _cache.update(at=now, stats=stats)
    return stats


def presets_payload(db, user=None):
    syms = preset_symbols(db)
    stats = preset_stats(db)
    return {
        "recommended": RECOMMENDED_PRESET, "window_days": WINDOW_DAYS,
        "current": current_preset(user, syms) if user is not None else None,
        "deviations": deviations(user) if user is not None else [],
        "presets": [{"key": k, "symbols": syms[k], "stats": stats.get(k)} for k in PRESET_KEYS],
    }
