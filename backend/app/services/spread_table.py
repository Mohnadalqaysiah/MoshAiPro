"""
spread_table.py — سبريد واقعي تقريبي لكل أداة (2026-10-09)
============================================================
مصدر واحد يقرأه المحرك (حد أدنى لمسافة الستوب، _institutional_gate) وسكربت
التشخيص diag_sl_vs_spread.py — حتى لا تنحرف الأرقام بين ما قيس وما طُبّق.

القيم بوحدة السعر: متوسط وسطاء التجزئة الشائعين بساعات التداول العادية.
تقدير محافظ لا قياس حي. رمز غير موجود هنا → None → لا يُطبَّق عليه الحد.
"""
from typing import Optional

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

# أسهم الخليج: التيك 0.01-0.05 حسب السعر — السبريد ≈ تيكين
GULF_STOCKS = {"ARAMCO", "RAJHI", "SABIC", "STC", "SNB", "MAADEN", "ALMARAI", "BAHRI",
               "ALINMA", "EMAAR", "EMIRATESNBD", "DIB", "FAB", "ADNOCDIST", "QNBK"}

# (2026-10-09) مسافة الستوب يجب ألا تقل عن هذا المضاعف من السبريد.
# مُعايَر بـdiag_sl_vs_spread.py على 566 قراراً فريداً منذ 2026-09-16:
# الشريحة < 3× وحدها خاسرة (24% نجاح، −0.12R)، وكل ما فوقها رابح
# (3-5×: +0.20R، 5-10×: +0.25R، ≥10×: +0.30R). راجع DECISIONS.md.
MIN_SL_SPREAD_MULT = 3.0


def typical_spread(symbol: str, entry: float) -> Optional[float]:
    sym = (symbol or "").upper()
    if sym in TYPICAL_SPREAD:
        return TYPICAL_SPREAD[sym]
    if sym in GULF_STOCKS:
        return 0.02 if entry < 10 else 0.04 if entry < 50 else 0.10
    return None
