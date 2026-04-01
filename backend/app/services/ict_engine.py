"""
Mosh AI Pro v5 - ICT / SMC Professional Engine
==============================================
خبرة 10+ سنوات في تداول ICT/SMC

يشمل:
- Order Blocks (Bullish/Bearish) - الخوارزمية الحقيقية
- Fair Value Gaps (FVG)
- Break of Structure (BOS) + Change of Character (CHoCH)
- Equal Highs/Lows (Liquidity Pools)
- Premium/Discount Zones (Fibonacci)
- Kill Zones (London/NY/Asia timing)
- Confluence Scoring (نقاط التقاطع)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from loguru import logger


class ICTEngine:
    """
    محرك ICT/SMC الاحترافي

    نظرية ICT الأساسية:
    - Smart Money (البنوك والمؤسسات) تتلاعب بالسوق لإيجاد السيولة
    - تبحث عن مناطق Stop Loss (Equal H/L) وتكسرها قبل الانعكاس
    - تدخل في Order Blocks وتترك FVG للملء
    - تتحرك في Kill Zones (أوقات السيولة العالية)
    """

    # ─── Swing Points ────────────────────────────────────────────────────────

    def find_swing_points(self, df: pd.DataFrame, strength: int = 5) -> Tuple[List, List]:
        """
        إيجاد نقاط التأرجح (Swing Highs & Lows) الحقيقية

        strength: عدد الشموع لكل جانب للتأكيد
        """
        highs = []
        lows = []
        n = len(df)

        for i in range(strength, n - strength):
            h = df["high"].iloc[i]
            l = df["low"].iloc[i]

            # Swing High: أعلى من كل الشموع على اليمين واليسار
            is_sh = all(h >= df["high"].iloc[i - j] for j in range(1, strength + 1)) and \
                    all(h >= df["high"].iloc[i + j] for j in range(1, strength + 1))

            # Swing Low: أقل من كل الشموع على اليمين واليسار
            is_sl = all(l <= df["low"].iloc[i - j] for j in range(1, strength + 1)) and \
                    all(l <= df["low"].iloc[i + j] for j in range(1, strength + 1))

            if is_sh:
                highs.append({
                    "index": i,
                    "price": float(h),
                    "datetime": str(df.get("datetime", pd.Series(range(n))).iloc[i] if "datetime" in df.columns else i)
                })

            if is_sl:
                lows.append({
                    "index": i,
                    "price": float(l),
                    "datetime": str(df.get("datetime", pd.Series(range(n))).iloc[i] if "datetime" in df.columns else i)
                })

        return highs, lows

    # ─── Order Blocks ─────────────────────────────────────────────────────────

    def detect_order_blocks(self, df: pd.DataFrame) -> Dict:
        """
        كشف Order Blocks الحقيقية بخوارزمية ICT

        Bullish OB: آخر شمعة هابطة قبل حركة صاعدة قوية (impulse)
        Bearish OB: آخر شمعة صاعدة قبل حركة هابطة قوية

        شروط الـ Impulse:
        - 3+ شموع متتالية في نفس الاتجاه
        - حجم الحركة > ATR
        """
        bullish_obs = []
        bearish_obs = []
        atr = df["atr"].iloc[-1] if "atr" in df.columns else (df["high"] - df["low"]).mean()
        n = len(df)

        for i in range(3, n - 3):
            # === Bullish OB ===
            # ابحث عن: شمعة هابطة (i) ثم impulse صاعدة
            if df["close"].iloc[i] < df["open"].iloc[i]:  # شمعة هابطة
                # تحقق impulse صاعد بعدها (على الأقل 2 شموع صاعدة قوية)
                impulse_up = 0
                for j in range(1, 4):
                    if i + j < n:
                        c = df["close"].iloc[i + j]
                        o = df["open"].iloc[i + j]
                        if c > o and (c - o) > atr * 0.3:
                            impulse_up += 1

                if impulse_up >= 2:
                    ob_high = float(df["high"].iloc[i])
                    ob_low = float(df["low"].iloc[i])
                    ob_mid = (ob_high + ob_low) / 2

                    # هل تم تخفيف الـ OB (mitigated)؟
                    current_price = float(df["close"].iloc[-1])
                    mitigated = current_price > ob_high  # تجاوز الـ OB

                    # المسافة من السعر الحالي
                    dist_pct = abs(current_price - ob_mid) / current_price * 100

                    if dist_pct < 5 and not mitigated:  # OB قريب وغير مُستَخدَم
                        bullish_obs.append({
                            "type": "BULLISH",
                            "high": ob_high,
                            "low": ob_low,
                            "mid": ob_mid,
                            "index": i,
                            "distance_pct": round(dist_pct, 3),
                            "mitigated": mitigated,
                            "strength": "STRONG" if impulse_up >= 3 else "MODERATE"
                        })

            # === Bearish OB ===
            # شمعة صاعدة (i) ثم impulse هابطة
            if df["close"].iloc[i] > df["open"].iloc[i]:  # شمعة صاعدة
                impulse_down = 0
                for j in range(1, 4):
                    if i + j < n:
                        c = df["close"].iloc[i + j]
                        o = df["open"].iloc[i + j]
                        if c < o and (o - c) > atr * 0.3:
                            impulse_down += 1

                if impulse_down >= 2:
                    ob_high = float(df["high"].iloc[i])
                    ob_low = float(df["low"].iloc[i])
                    ob_mid = (ob_high + ob_low) / 2
                    current_price = float(df["close"].iloc[-1])
                    mitigated = current_price < ob_low
                    dist_pct = abs(current_price - ob_mid) / current_price * 100

                    if dist_pct < 5 and not mitigated:
                        bearish_obs.append({
                            "type": "BEARISH",
                            "high": ob_high,
                            "low": ob_low,
                            "mid": ob_mid,
                            "index": i,
                            "distance_pct": round(dist_pct, 3),
                            "mitigated": mitigated,
                            "strength": "STRONG" if impulse_down >= 3 else "MODERATE"
                        })

        # أحدث 3 OBs فقط (الأقرب للسعر)
        bullish_obs = sorted(bullish_obs, key=lambda x: x["distance_pct"])[:3]
        bearish_obs = sorted(bearish_obs, key=lambda x: x["distance_pct"])[:3]

        # هل السعر داخل OB؟
        current = float(df["close"].iloc[-1])
        in_bullish_ob = any(ob["low"] <= current <= ob["high"] for ob in bullish_obs)
        in_bearish_ob = any(ob["low"] <= current <= ob["high"] for ob in bearish_obs)

        return {
            "bullish_obs": bullish_obs,
            "bearish_obs": bearish_obs,
            "in_bullish_ob": in_bullish_ob,
            "in_bearish_ob": in_bearish_ob,
            "nearest_bullish": bullish_obs[0] if bullish_obs else None,
            "nearest_bearish": bearish_obs[0] if bearish_obs else None,
        }

    # ─── Fair Value Gaps ──────────────────────────────────────────────────────

    def detect_fvg(self, df: pd.DataFrame) -> Dict:
        """
        كشف Fair Value Gaps (الفجوات السعرية)

        Bullish FVG: فجوة صاعدة بين شمعة (i-2) وشمعة (i)
            شرط: low[i] > high[i-2]

        Bearish FVG: فجوة هابطة
            شرط: high[i] < low[i-2]
        """
        bullish_fvgs = []
        bearish_fvgs = []
        current = float(df["close"].iloc[-1])
        n = len(df)

        for i in range(2, n):
            h_prev2 = float(df["high"].iloc[i - 2])
            l_prev2 = float(df["low"].iloc[i - 2])
            h_curr = float(df["high"].iloc[i])
            l_curr = float(df["low"].iloc[i])

            # Bullish FVG
            if l_curr > h_prev2:
                gap_size = l_curr - h_prev2
                gap_mid = (l_curr + h_prev2) / 2
                # هل مملوءة؟
                filled = current <= l_curr  # السعر دخل الفجوة
                dist_pct = abs(current - gap_mid) / current * 100

                if dist_pct < 8 and not filled:
                    bullish_fvgs.append({
                        "type": "BULLISH",
                        "top": l_curr,
                        "bottom": h_prev2,
                        "mid": gap_mid,
                        "size": round(gap_size, 5),
                        "size_pct": round(gap_size / current * 100, 3),
                        "index": i,
                        "filled": filled,
                        "distance_pct": round(dist_pct, 3),
                    })

            # Bearish FVG
            elif h_curr < l_prev2:
                gap_size = l_prev2 - h_curr
                gap_mid = (l_prev2 + h_curr) / 2
                filled = current >= h_curr
                dist_pct = abs(current - gap_mid) / current * 100

                if dist_pct < 8 and not filled:
                    bearish_fvgs.append({
                        "type": "BEARISH",
                        "top": l_prev2,
                        "bottom": h_curr,
                        "mid": gap_mid,
                        "size": round(gap_size, 5),
                        "size_pct": round(gap_size / current * 100, 3),
                        "index": i,
                        "filled": filled,
                        "distance_pct": round(dist_pct, 3),
                    })

        # أحدث 5 FVGs
        bullish_fvgs = sorted(bullish_fvgs, key=lambda x: x["index"], reverse=True)[:5]
        bearish_fvgs = sorted(bearish_fvgs, key=lambda x: x["index"], reverse=True)[:5]

        # هل السعر داخل FVG؟
        in_bullish_fvg = any(fvg["bottom"] <= current <= fvg["top"] for fvg in bullish_fvgs)
        in_bearish_fvg = any(fvg["bottom"] <= current <= fvg["top"] for fvg in bearish_fvgs)

        return {
            "bullish_fvgs": bullish_fvgs,
            "bearish_fvgs": bearish_fvgs,
            "in_bullish_fvg": in_bullish_fvg,
            "in_bearish_fvg": in_bearish_fvg,
            "nearest_bullish": bullish_fvgs[0] if bullish_fvgs else None,
            "nearest_bearish": bearish_fvgs[0] if bearish_fvgs else None,
        }

    # ─── BOS & CHoCH ─────────────────────────────────────────────────────────

    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        تحليل هيكل السوق الحقيقي بناءً على Swing Points

        BOS: كسر هيكلي - السعر يتجاوز Swing High/Low السابق
        CHoCH: تغيير الطابع - أول BOS عكسي بعد ترند
        """
        highs, lows = self.find_swing_points(df, strength=3)

        if len(highs) < 2 or len(lows) < 2:
            return {
                "trend": "RANGING",
                "bos_events": [],
                "choch_events": [],
                "last_bos": None,
                "structure": "UNKNOWN",
                "confidence": 40.0
            }

        # تحديد الترند بناءً على HH/HL أو LH/LL
        last_highs = highs[-3:] if len(highs) >= 3 else highs
        last_lows = lows[-3:] if len(lows) >= 3 else lows

        hh = last_highs[-1]["price"] > last_highs[-2]["price"] if len(last_highs) >= 2 else False
        hl = last_lows[-1]["price"] > last_lows[-2]["price"] if len(last_lows) >= 2 else False
        lh = last_highs[-1]["price"] < last_highs[-2]["price"] if len(last_highs) >= 2 else False
        ll = last_lows[-1]["price"] < last_lows[-2]["price"] if len(last_lows) >= 2 else False

        # هيكل السوق
        if hh and hl:
            structure = "HH_HL"
            trend = "BULLISH"
            conf = 80.0
        elif lh and ll:
            structure = "LH_LL"
            trend = "BEARISH"
            conf = 80.0
        elif hh and ll:
            structure = "HH_LL"
            trend = "RANGING"
            conf = 50.0
        elif lh and hl:
            structure = "LH_HL"
            trend = "RANGING"
            conf = 50.0
        else:
            structure = "MIXED"
            trend = "RANGING"
            conf = 40.0

        # BOS Events
        bos_events = []
        current = float(df["close"].iloc[-1])

        # آخر Swing High كُسر → Bullish BOS
        for sh in reversed(last_highs[:-1]):
            if current > sh["price"]:
                bos_events.append({
                    "type": "BULLISH_BOS",
                    "level": sh["price"],
                    "description": f"BOS فوق {sh['price']:.5f}"
                })
                break

        # آخر Swing Low كُسر → Bearish BOS
        for sl in reversed(last_lows[:-1]):
            if current < sl["price"]:
                bos_events.append({
                    "type": "BEARISH_BOS",
                    "level": sl["price"],
                    "description": f"BOS تحت {sl['price']:.5f}"
                })
                break

        # CHoCH: أول BOS عكسي
        choch_events = []
        if trend == "BULLISH" and any("BEARISH" in b["type"] for b in bos_events):
            choch_events.append({
                "type": "BEARISH_CHOCH",
                "description": "تغيير طابع محتمل → ابتعد عن البيع"
            })
        elif trend == "BEARISH" and any("BULLISH" in b["type"] for b in bos_events):
            choch_events.append({
                "type": "BULLISH_CHOCH",
                "description": "تغيير طابع محتمل → ابتعد عن الشراء"
            })

        last_bos = bos_events[-1] if bos_events else None

        return {
            "trend": trend,
            "structure": structure,
            "bos_events": bos_events,
            "choch_events": choch_events,
            "last_bos": last_bos,
            "swing_highs": [h["price"] for h in last_highs],
            "swing_lows": [l["price"] for l in last_lows],
            "confidence": conf
        }

    # ─── Equal Highs/Lows (Liquidity Pools) ──────────────────────────────────

    def detect_liquidity_pools(self, df: pd.DataFrame, tolerance: float = 0.002) -> Dict:
        """
        كشف مستويات السيولة (Equal Highs/Lows)

        البنوك تستهدف هذه المستويات لأنها تعلم أن Stop Loss المتداولين هناك
        tolerance: 0.2% فرق مقبول بين القمتين
        """
        highs, lows = self.find_swing_points(df, strength=3)
        current = float(df["close"].iloc[-1])

        equal_highs = []
        equal_lows = []

        # Equal Highs (BSL - Buy Side Liquidity)
        for i in range(len(highs)):
            for j in range(i + 1, len(highs)):
                diff = abs(highs[i]["price"] - highs[j]["price"]) / highs[i]["price"]
                if diff <= tolerance:
                    level = (highs[i]["price"] + highs[j]["price"]) / 2
                    dist = abs(current - level) / current * 100
                    equal_highs.append({
                        "level": round(level, 5),
                        "type": "BSL",  # Buy Side Liquidity
                        "description": "Equal Highs - سيولة شرائية",
                        "distance_pct": round(dist, 3),
                        "swept": current > level
                    })

        # Equal Lows (SSL - Sell Side Liquidity)
        for i in range(len(lows)):
            for j in range(i + 1, len(lows)):
                diff = abs(lows[i]["price"] - lows[j]["price"]) / lows[i]["price"]
                if diff <= tolerance:
                    level = (lows[i]["price"] + lows[j]["price"]) / 2
                    dist = abs(current - level) / current * 100
                    equal_lows.append({
                        "level": round(level, 5),
                        "type": "SSL",  # Sell Side Liquidity
                        "description": "Equal Lows - سيولة بيعية",
                        "distance_pct": round(dist, 3),
                        "swept": current < level
                    })

        # أقرب مستويات غير مُكتسَحة
        unswept_highs = [h for h in equal_highs if not h["swept"]]
        unswept_lows = [l for l in equal_lows if not l["swept"]]

        unswept_highs = sorted(unswept_highs, key=lambda x: x["distance_pct"])[:3]
        unswept_lows = sorted(unswept_lows, key=lambda x: x["distance_pct"])[:3]

        # البيئة: هل السيولة فوق أم تحت؟
        bias = "NEUTRAL"
        if unswept_highs and unswept_lows:
            if unswept_highs[0]["distance_pct"] < unswept_lows[0]["distance_pct"]:
                bias = "BEARISH"  # السيولة أعلى → السوق قد يصعد ليكتسحها ثم يهبط
            else:
                bias = "BULLISH"  # السيولة أسفل → قد يهبط ليكتسحها ثم يصعد

        # نحتفظ أيضاً بالمستويات المُكتسَحة لاستخدامها في كاشف Stop Hunt
        swept_highs = sorted([h for h in equal_highs if h["swept"]],
                             key=lambda x: x["distance_pct"])[:3]
        swept_lows  = sorted([l for l in equal_lows  if l["swept"]],
                             key=lambda x: x["distance_pct"])[:3]

        return {
            "equal_highs":  unswept_highs,
            "equal_lows":   unswept_lows,
            "swept_highs":  swept_highs,   # BSL مُكتسَح مؤخراً
            "swept_lows":   swept_lows,    # SSL مُكتسَح مؤخراً
            "bias":         bias,
            "nearest_bsl":  unswept_highs[0]["level"] if unswept_highs else None,
            "nearest_ssl":  unswept_lows[0]["level"]  if unswept_lows  else None,
        }

    # ─── Liquidity Sweep / Stop Hunt Detection ────────────────────────────────

    def detect_liquidity_sweeps(self, df: pd.DataFrame, liquidity: Dict) -> Dict:
        """
        كاشف اكتساح السيولة وصيد الـ Stop Loss (Stop Hunt)

        Smart Money تسحب السيولة قبل الانعكاس:
        - SSL Stop Hunt: الشمعة تنخفض تحت قاع → تُغلق فوقه → BUY
        - BSL Stop Hunt: الشمعة ترتفع فوق قمة → تُغلق تحتها → SELL

        تُعيد:
        - ssl_sweep / bsl_sweep: تفاصيل أفضل اكتساح مؤخراً
        - has_bullish_sweep / has_bearish_sweep: هل الاكتساح مع رفض مؤكد؟
        - sweep_quality: STRONG / MODERATE / WEAK / NONE
        """
        if len(df) < 10:
            return {"has_bullish_sweep": False, "has_bearish_sweep": False, "sweep_quality": "NONE"}

        # ATR كمرجع للحجم
        atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else float((df["high"] - df["low"]).mean())
        if atr <= 0:
            atr = 1.0

        # ── مستويات السيولة من detect_liquidity_pools ─────────────────────────
        bsl_levels = [h["level"] for h in liquidity.get("equal_highs", [])]
        ssl_levels = [l["level"] for l in liquidity.get("equal_lows",  [])]

        # نضيف أيضاً swing highs/lows الفردية كمستويات سيولة فردية
        highs_sp, lows_sp = self.find_swing_points(df, strength=3)
        lookback = max(0, len(df) - int(len(df) * 0.4))  # آخر 40% من البيانات
        bsl_levels += [h["price"] for h in highs_sp if h["index"] >= lookback]
        ssl_levels += [l["price"] for l in lows_sp  if l["index"] >= lookback]

        # إزالة التكرار (مستويات متقاربة جداً تُدمج)
        def _deduplicate(levels, tol_pct=0.001):
            out = []
            for lvl in sorted(set(levels)):
                if not out or abs(lvl - out[-1]) / lvl > tol_pct:
                    out.append(lvl)
            return out

        bsl_levels = _deduplicate(bsl_levels)
        ssl_levels = _deduplicate(ssl_levels)

        # ── مسح آخر 15 شمعة بحثاً عن اكتساح + رفض ───────────────────────────
        scan_window = min(15, len(df) - 2)
        scan_df = df.iloc[-(scan_window + 1):-1]  # نستثني الشمعة الحالية

        best_bsl_sweep = None
        best_ssl_sweep = None

        for i, (_, row) in enumerate(scan_df.iterrows()):
            hi    = float(row["high"])
            lo    = float(row["low"])
            cl    = float(row["close"])
            op    = float(row["open"])
            candles_since = scan_window - i  # 1 = الشمعة الأخيرة

            # ── BSL Stop Hunt (هبوط بعد سحب سيولة فوق القمم) ─────────────────
            for level in bsl_levels:
                if hi > level and cl < level:
                    wick_above   = hi - level
                    body_below   = level - cl
                    wick_ratio   = wick_above / atr

                    confirmed = (
                        wick_above  > atr * 0.25 and   # شوكة واضحة فوق المستوى
                        body_below  > atr * 0.05 and   # الإغلاق داخل الرينج
                        cl < op                         # شمعة هبوطية
                    )
                    info = {
                        "level":             round(level, 5),
                        "wick_magnitude":    round(wick_above, 5),
                        "wick_atr_ratio":    round(wick_ratio, 2),
                        "rejection_confirmed": confirmed,
                        "candles_since":     candles_since,
                    }
                    if best_bsl_sweep is None or (
                        confirmed and not best_bsl_sweep["rejection_confirmed"]
                    ) or (
                        confirmed == best_bsl_sweep["rejection_confirmed"]
                        and candles_since < best_bsl_sweep["candles_since"]
                    ):
                        best_bsl_sweep = info

            # ── SSL Stop Hunt (صعود بعد سحب سيولة تحت القيعان) ───────────────
            for level in ssl_levels:
                if lo < level and cl > level:
                    wick_below   = level - lo
                    body_above   = cl - level
                    wick_ratio   = wick_below / atr

                    confirmed = (
                        wick_below > atr * 0.25 and
                        body_above > atr * 0.05 and
                        cl > op                         # شمعة صعودية
                    )
                    info = {
                        "level":             round(level, 5),
                        "wick_magnitude":    round(wick_below, 5),
                        "wick_atr_ratio":    round(wick_ratio, 2),
                        "rejection_confirmed": confirmed,
                        "candles_since":     candles_since,
                    }
                    if best_ssl_sweep is None or (
                        confirmed and not best_ssl_sweep["rejection_confirmed"]
                    ) or (
                        confirmed == best_ssl_sweep["rejection_confirmed"]
                        and candles_since < best_ssl_sweep["candles_since"]
                    ):
                        best_ssl_sweep = info

        # ── جودة الاكتساح ─────────────────────────────────────────────────────
        has_bullish_sweep = bool(best_ssl_sweep and best_ssl_sweep["rejection_confirmed"])
        has_bearish_sweep = bool(best_bsl_sweep and best_bsl_sweep["rejection_confirmed"])

        if has_bullish_sweep or has_bearish_sweep:
            sweep = best_ssl_sweep if has_bullish_sweep else best_bsl_sweep
            if sweep["candles_since"] <= 5 and sweep["wick_atr_ratio"] >= 0.5:
                quality = "STRONG"    # اكتساح حديث + شوكة قوية
            else:
                quality = "MODERATE"  # اكتساح مؤكد لكن أقدم أو أضعف
        elif best_bsl_sweep or best_ssl_sweep:
            quality = "WEAK"          # اكتساح بدون رفض مؤكد
        else:
            quality = "NONE"

        return {
            "bsl_sweep":        best_bsl_sweep,
            "ssl_sweep":        best_ssl_sweep,
            "has_bullish_sweep": has_bullish_sweep,
            "has_bearish_sweep": has_bearish_sweep,
            "sweep_quality":    quality,
        }

    # ─── Premium / Discount Zones ─────────────────────────────────────────────

    def analyze_premium_discount(self, df: pd.DataFrame) -> Dict:
        """
        تحديد مناطق Premium/Discount بناءً على Fibonacci 50%

        Premium (فوق 50%): مناسب للبيع
        Discount (تحت 50%): مناسب للشراء
        Equilibrium (50%): منطقة محايدة
        """
        recent_high = float(df["high"].tail(50).max())
        recent_low = float(df["low"].tail(50).min())
        current = float(df["close"].iloc[-1])

        swing_range = recent_high - recent_low
        if swing_range == 0:
            return {"zone": "UNKNOWN", "pct": 50, "confidence": 0}

        # موقع السعر كنسبة مئوية
        pct = (current - recent_low) / swing_range * 100

        # Fibonacci مستويات مهمة
        fib_levels = {
            "0.0": recent_low,
            "0.236": recent_low + swing_range * 0.236,
            "0.382": recent_low + swing_range * 0.382,
            "0.5": recent_low + swing_range * 0.5,    # Equilibrium
            "0.618": recent_low + swing_range * 0.618, # Optimal Trade Entry
            "0.786": recent_low + swing_range * 0.786,
            "1.0": recent_high,
        }

        # تحديد المنطقة
        if pct >= 75:
            zone = "EXTREME_PREMIUM"
            bias = "SELL"
            conf = 85.0
        elif pct >= 55:
            zone = "PREMIUM"
            bias = "SELL"
            conf = 70.0
        elif 45 <= pct < 55:
            zone = "EQUILIBRIUM"
            bias = "NEUTRAL"
            conf = 50.0
        elif pct >= 25:
            zone = "DISCOUNT"
            bias = "BUY"
            conf = 70.0
        else:
            zone = "EXTREME_DISCOUNT"
            bias = "BUY"
            conf = 85.0

        return {
            "zone": zone,
            "bias": bias,
            "pct": round(pct, 1),
            "current": current,
            "swing_high": recent_high,
            "swing_low": recent_low,
            "equilibrium": fib_levels["0.5"],
            "ote_level": fib_levels["0.618"],  # Optimal Trade Entry
            "fib_levels": {k: round(v, 5) for k, v in fib_levels.items()},
            "confidence": conf,
        }

    # ─── Kill Zones ────────────────────────────────────────────────────────────

    def get_kill_zone(self) -> Dict:
        """
        Kill Zones الحقيقية بتوقيت UTC:

        - Asia KZ: 00:00 - 04:00 UTC
        - London Open KZ: 07:00 - 09:00 UTC (الأقوى)
        - New York Open KZ: 13:30 - 15:30 UTC (الأقوى)
        - London Close: 11:00 - 13:00 UTC
        - Midnight Open: 23:00 - 01:00 UTC
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        time_decimal = hour + minute / 60

        sessions = {
            "Asia": (0, 4),
            "London_Open": (7, 9),      # الأفضل
            "London_Close": (11, 13),
            "New_York_Open": (13.5, 15.5),  # الأفضل
            "Midnight_Open": (23, 25),   # 23:00-01:00
        }

        active_session = None
        is_kill_zone = False
        is_optimal = False  # London/NY فقط

        for session, (start, end) in sessions.items():
            # Midnight crosses midnight
            if start == 23:
                in_session = time_decimal >= 23 or time_decimal < 1
            else:
                in_session = start <= time_decimal < end

            if in_session:
                active_session = session
                is_kill_zone = True
                is_optimal = session in ["London_Open", "New_York_Open"]
                break

        # الجلسة التالية
        next_sessions = {
            "London_Open": "07:00 UTC",
            "New_York_Open": "13:30 UTC",
            "Asia": "00:00 UTC",
        }
        next_major = None
        for sess, time_str in next_sessions.items():
            if sess != active_session:
                next_major = {"session": sess, "time": time_str}
                break

        conf = 90 if is_optimal else (60 if is_kill_zone else 20)

        return {
            "current_time_utc": now.strftime("%H:%M UTC"),
            "active_session": active_session or "Inter-Session",
            "is_kill_zone": is_kill_zone,
            "is_optimal_time": is_optimal,
            "next_major_session": next_major,
            "confidence": conf,
            "recommendation": (
                "وقت ممتاز للدخول" if is_optimal else
                "وقت جيد" if is_kill_zone else
                "انتظر Kill Zone القادم"
            )
        }

    # ─── Wyckoff Analysis ─────────────────────────────────────────────────────

    def analyze_wyckoff(self, df: pd.DataFrame) -> Dict:
        """
        تحليل Wyckoff المبسط لكنه فعّال

        Accumulation: تراكم (الشراء الذكي)
        Markup: ارتفاع
        Distribution: توزيع (البيع الذكي)
        Markdown: انخفاض
        """
        if len(df) < 50:
            return {"phase": "UNKNOWN", "action": "WAIT", "confidence": 0}

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))

        # حساب المتوسطات
        ma_20 = close.rolling(20).mean()
        ma_50 = close.rolling(50).mean()
        current = float(close.iloc[-1])
        ma20_v = float(ma_20.iloc[-1])
        ma50_v = float(ma_50.iloc[-1])

        # Volume analysis
        avg_vol = float(volume.rolling(20).mean().iloc[-1]) if float(volume.sum()) > 0 else 1
        current_vol = float(volume.iloc[-1]) if float(volume.sum()) > 0 else 1
        high_volume = current_vol > avg_vol * 1.5

        # اتجاه السعر
        price_trend_20 = (current - float(close.iloc[-20])) / float(close.iloc[-20]) * 100
        price_trend_5 = (current - float(close.iloc[-5])) / float(close.iloc[-5]) * 100

        # تحديد الـ Phase
        if current > ma20_v > ma50_v:
            if price_trend_5 > 0.3:
                phase = "MARKUP"
                action = "BUY_SIGNAL"
                conf = 75
            else:
                phase = "DISTRIBUTION_START"
                action = "PREPARE_SELL"
                conf = 60
        elif current < ma20_v < ma50_v:
            if price_trend_5 < -0.3:
                phase = "MARKDOWN"
                action = "SELL_SIGNAL"
                conf = 75
            else:
                phase = "ACCUMULATION_START"
                action = "PREPARE_BUY"
                conf = 60
        elif abs(price_trend_20) < 1.5:
            # في نطاق ضيق = Accumulation أو Distribution
            if high_volume:
                phase = "ACCUMULATION" if price_trend_5 > 0 else "DISTRIBUTION"
                action = "PREPARE_BUY" if price_trend_5 > 0 else "PREPARE_SELL"
                conf = 65
            else:
                phase = "RANGING"
                action = "WAIT"
                conf = 40
        else:
            phase = "TRANSITION"
            action = "WAIT"
            conf = 35

        return {
            "phase": phase,
            "action": action,
            "confidence": float(conf),
            "trend_20_pct": round(price_trend_20, 2),
            "trend_5_pct": round(price_trend_5, 2),
            "high_volume": high_volume,
        }

    # ─── Confluence Scorer ────────────────────────────────────────────────────

    def calculate_confluence(
        self,
        structure: Dict,
        order_blocks: Dict,
        fvg: Dict,
        liquidity: Dict,
        premium_discount: Dict,
        kill_zone: Dict,
        wyckoff: Dict,
        df: pd.DataFrame
    ) -> Dict:
        """
        نظام نقاط التقاطع - الأكثر أهمية في ICT

        الفكرة: كل عامل يؤكد الفرصة يضيف نقاط
        نحتاج على الأقل 3 عوامل للدخول
        """

        bull_score = 0
        bear_score = 0
        bull_factors = []
        bear_factors = []
        current = float(df["close"].iloc[-1])

        # ── 1. Market Structure (20 نقطة) ──────────────────────────────────
        trend = structure.get("trend", "RANGING")
        if trend == "BULLISH":
            bull_score += 20
            bull_factors.append(f"BOS صاعد ({structure.get('structure', '')})")
        elif trend == "BEARISH":
            bear_score += 20
            bear_factors.append(f"BOS هابط ({structure.get('structure', '')})")

        # ── 2. Order Block (25 نقطة) ─────────────────────────────────────────
        if order_blocks.get("in_bullish_ob"):
            bull_score += 25
            ob = order_blocks.get("nearest_bullish", {})
            bull_factors.append(f"Order Block صاعد @ {ob.get('low', 0):.5f}-{ob.get('high', 0):.5f}")
        if order_blocks.get("in_bearish_ob"):
            bear_score += 25
            ob = order_blocks.get("nearest_bearish", {})
            bear_factors.append(f"Order Block هابط @ {ob.get('low', 0):.5f}-{ob.get('high', 0):.5f}")

        # ── 3. Fair Value Gap (15 نقطة) ──────────────────────────────────────
        if fvg.get("in_bullish_fvg"):
            bull_score += 15
            bull_factors.append("السعر في FVG صاعد")
        elif fvg.get("bullish_fvgs"):
            nearest = fvg["bullish_fvgs"][0]
            if nearest["distance_pct"] < 0.5:
                bull_score += 8
                bull_factors.append(f"FVG صاعد قريب جداً ({nearest['distance_pct']:.2f}%)")

        if fvg.get("in_bearish_fvg"):
            bear_score += 15
            bear_factors.append("السعر في FVG هابط")
        elif fvg.get("bearish_fvgs"):
            nearest = fvg["bearish_fvgs"][0]
            if nearest["distance_pct"] < 0.5:
                bear_score += 8
                bear_factors.append(f"FVG هابط قريب جداً ({nearest['distance_pct']:.2f}%)")

        # ── 4. Premium/Discount Zone (15 نقطة) ────────────────────────────────
        pd_bias = premium_discount.get("bias", "NEUTRAL")
        pd_zone = premium_discount.get("zone", "UNKNOWN")
        if pd_bias == "BUY":
            pts = 15 if "EXTREME" in pd_zone else 10
            bull_score += pts
            bull_factors.append(f"منطقة {pd_zone} ({premium_discount.get('pct', 0):.1f}%)")
        elif pd_bias == "SELL":
            pts = 15 if "EXTREME" in pd_zone else 10
            bear_score += pts
            bear_factors.append(f"منطقة {pd_zone} ({premium_discount.get('pct', 0):.1f}%)")

        # ── 5. Liquidity Sweep + Stop Hunt (25 نقطة) ─────────────────────────────
        # الاكتساح مع رفض = شرط ICT / SMC الأساسي للدخول
        sweep = liquidity.get("sweep_analysis", {})
        sq    = sweep.get("sweep_quality", "NONE")

        if sweep.get("has_bullish_sweep"):
            # SSL Stop Hunt مؤكد → صعود
            pts = 25 if sq == "STRONG" else 15
            bull_score += pts
            ssl_info = sweep.get("ssl_sweep", {})
            bull_factors.append(
                f"✅ Stop Hunt SSL مؤكد — منذ {ssl_info.get('candles_since','?')} شمعة"
                f" (شوكة {ssl_info.get('wick_atr_ratio','?')}x ATR)"
            )
        elif sweep.get("ssl_sweep"):
            # SSL مُكتسَح لكن بدون رفض واضح
            bull_score += 5
            ssl_info = sweep.get("ssl_sweep", {})
            bull_factors.append(f"SSL مُكتسَح (رفض غير مؤكد — منذ {ssl_info.get('candles_since','?')} شمعة)")

        if sweep.get("has_bearish_sweep"):
            # BSL Stop Hunt مؤكد → هبوط
            pts = 25 if sq == "STRONG" else 15
            bear_score += pts
            bsl_info = sweep.get("bsl_sweep", {})
            bear_factors.append(
                f"✅ Stop Hunt BSL مؤكد — منذ {bsl_info.get('candles_since','?')} شمعة"
                f" (شوكة {bsl_info.get('wick_atr_ratio','?')}x ATR)"
            )
        elif sweep.get("bsl_sweep"):
            bear_score += 5
            bsl_info = sweep.get("bsl_sweep", {})
            bear_factors.append(f"BSL مُكتسَح (رفض غير مؤكد — منذ {bsl_info.get('candles_since','?')} شمعة)")

        # عقوبة: لا يوجد اكتساح سيولة على الإطلاق → -8 نقاط لكلا الاتجاهين
        if sq == "NONE":
            bull_score = max(0, bull_score - 8)
            bear_score = max(0, bear_score - 8)

        # ── 6. Kill Zone (10 نقطة) ─────────────────────────────────────────────
        if kill_zone.get("is_optimal_time"):
            bull_score += 10
            bear_score += 10
            kz_msg = f"Kill Zone نشط: {kill_zone.get('active_session')}"
            bull_factors.append(kz_msg)
            bear_factors.append(kz_msg)
        elif kill_zone.get("is_kill_zone"):
            bull_score += 5
            bear_score += 5

        # ── 7. Wyckoff (10 نقطة) ─────────────────────────────────────────────
        wy_action = wyckoff.get("action", "WAIT")
        if wy_action in ["BUY_SIGNAL", "PREPARE_BUY"]:
            pts = 10 if wy_action == "BUY_SIGNAL" else 6
            bull_score += pts
            bull_factors.append(f"Wyckoff: {wyckoff.get('phase')}")
        elif wy_action in ["SELL_SIGNAL", "PREPARE_SELL"]:
            pts = 10 if wy_action == "SELL_SIGNAL" else 6
            bear_score += pts
            bear_factors.append(f"Wyckoff: {wyckoff.get('phase')}")

        # ── 8. RSI (5 نقطة) ────────────────────────────────────────────────────
        if "rsi" in df.columns:
            rsi = float(df["rsi"].iloc[-1])
            if rsi < 30:
                bull_score += 5
                bull_factors.append(f"RSI ذعر بيعي: {rsi:.1f}")
            elif rsi > 70:
                bear_score += 5
                bear_factors.append(f"RSI ذعر شرائي: {rsi:.1f}")

        # ── 9. MACD (5 نقطة) ──────────────────────────────────────────────────
        if "macd" in df.columns:
            macd = float(df["macd"].iloc[-1])
            macd_signal = float(df["macd_signal"].iloc[-1])
            macd_hist_prev = float(df["macd_hist"].iloc[-2]) if len(df) > 2 else 0
            macd_hist_curr = float(df["macd_hist"].iloc[-1])

            # Bullish crossover
            if macd > macd_signal and macd_hist_curr > 0 and macd_hist_prev < 0:
                bull_score += 5
                bull_factors.append("MACD تقاطع صاعد")
            # Bearish crossover
            elif macd < macd_signal and macd_hist_curr < 0 and macd_hist_prev > 0:
                bear_score += 5
                bear_factors.append("MACD تقاطع هابط")

        # ── التقييم النهائي ─────────────────────────────────────────────────────
        max_score = 100  # مجموع النقاط الكامل

        bull_confidence = min(bull_score, max_score)
        bear_confidence = min(bear_score, max_score)

        if bull_confidence > bear_confidence and bull_confidence >= 40:
            direction = "BUY"
            confidence = bull_confidence
            factors = bull_factors
        elif bear_confidence > bull_confidence and bear_confidence >= 40:
            direction = "SELL"
            confidence = bear_confidence
            factors = bear_factors
        else:
            direction = "WAIT"
            confidence = max(bull_confidence, bear_confidence)
            factors = bull_factors + bear_factors

        # نقطة 3 عوامل كحد أدنى
        min_factors_met = len(factors) >= 3

        return {
            "direction": direction,
            "confidence": float(confidence),
            "bull_score": bull_score,
            "bear_score": bear_score,
            "factors": factors,
            "factor_count": len(factors),
            "min_factors_met": min_factors_met,
            "quality": (
                "PREMIUM" if confidence >= 75 and min_factors_met else
                "STANDARD" if confidence >= 55 and min_factors_met else
                "LOW"
            )
        }

    # ─── ATR-based Levels ────────────────────────────────────────────────────

    def calculate_levels(
        self,
        df: pd.DataFrame,
        direction: str,
        order_blocks: Dict,
        fvg: Dict,
        liquidity: Dict
    ) -> Dict:
        """
        حساب مستويات الدخول، وقف الخسارة، الأهداف
        بناءً على ATR وبنية السوق الحقيقية (ICT Method)
        """
        current = float(df["close"].iloc[-1])
        atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else current * 0.001
        highs, lows = self.find_swing_points(df, strength=3)

        if direction == "BUY":
            # الدخول: عند OB أو FVG الأقرب أو السعر الحالي
            entry = current
            ob = order_blocks.get("nearest_bullish")
            if ob and ob["distance_pct"] < 0.3:
                entry = ob["mid"]

            # وقف الخسارة: Swing Low أسفل entry فقط (ضروري)
            valid_lows = [l["price"] for l in lows if l["price"] < entry]
            if valid_lows:
                sl = max(valid_lows) - atr * 0.5   # أقرب low أسفل entry
            else:
                sl = entry - atr * 2

            # الأهداف: أعلى من entry (محسوبة من entry وليس current)
            bsl = liquidity.get("nearest_bsl")
            tp1 = entry + atr * 1.5
            tp2 = bsl if bsl and bsl > entry else entry + atr * 3
            tp3 = entry + atr * 5

        else:  # SELL
            entry = current
            ob = order_blocks.get("nearest_bearish")
            if ob and ob["distance_pct"] < 0.3:
                entry = ob["mid"]

            # وقف الخسارة: Swing High فوق entry فقط (ضروري)
            valid_highs = [h["price"] for h in highs if h["price"] > entry]
            if valid_highs:
                sl = min(valid_highs) + atr * 0.5  # أقرب high فوق entry
            else:
                sl = entry + atr * 2

            # الأهداف: أسفل من entry (محسوبة من entry وليس current)
            ssl = liquidity.get("nearest_ssl")
            tp1 = entry - atr * 1.5
            tp2 = ssl if ssl and ssl < entry else entry - atr * 3
            tp3 = entry - atr * 5

        # ─── تحقق إجباري: SL/TP في الاتجاه الصحيح ───────────────────────
        if direction == "BUY":
            if sl >= entry:
                sl = entry - atr * 2
            if tp1 <= entry:
                tp1 = entry + atr * 1.5
            if tp2 <= entry:
                tp2 = entry + atr * 3
            if tp3 <= entry:
                tp3 = entry + atr * 5
        else:
            if sl <= entry:
                sl = entry + atr * 2
            if tp1 >= entry:
                tp1 = entry - atr * 1.5
            if tp2 >= entry:
                tp2 = entry - atr * 3
            if tp3 >= entry:
                tp3 = entry - atr * 5

        # Risk/Reward
        risk = abs(entry - sl)
        reward_tp2 = abs(tp2 - entry)
        rr = round(reward_tp2 / risk, 2) if risk > 0 else 0

        # منطقة الدخول المهنية: ±25% من ATR حول نقطة الدخول المثالية
        zone_buffer = atr * 0.25
        return {
            "entry": round(entry, 5),
            "entry_zone_min": round(entry - zone_buffer, 5),
            "entry_zone_max": round(entry + zone_buffer, 5),
            "stop_loss": round(sl, 5),
            "tp1": round(tp1, 5),
            "tp2": round(tp2, 5),
            "tp3": round(tp3, 5),
            "risk_pips": round(risk, 5),
            "risk_reward": rr,
            "atr": round(atr, 5),
        }

    # ─── Market Mode Detection ────────────────────────────────────────────────

    def detect_market_mode(self, df: pd.DataFrame, wyckoff: dict, structure: dict) -> dict:
        """
        تحديد وضع السوق: TREND أو RANGE
        TREND: Wyckoff Markup/Markdown + BOS + اتجاه واضح → Sweep اختياري
        RANGE: Accumulation/Distribution أو Sideways → Sweep إجباري
        """
        phase = (wyckoff.get("phase") or "").upper()
        trend = (structure.get("trend") or "SIDEWAYS").upper()
        has_bos = bool(structure.get("last_bos"))

        trend_indicators = ["MARKUP", "MARKDOWN", "UPTREND", "DOWNTREND"]
        range_indicators  = ["ACCUMULATION", "DISTRIBUTION", "SIDEWAYS", "RANGING"]

        is_trend_phase = any(p in phase for p in trend_indicators)
        is_range_phase = any(p in phase for p in range_indicators) or trend == "SIDEWAYS"

        if is_trend_phase and has_bos:
            mode, confidence, sweep_required = "TREND", 85, False
        elif has_bos and trend in ("BULLISH", "BEARISH"):
            mode, confidence, sweep_required = "TREND", 65, False
        else:
            mode, confidence, sweep_required = "RANGE", 70, True

        return {
            "mode":           mode,
            "confidence":     confidence,
            "sweep_required": sweep_required,
            "wyckoff_phase":  wyckoff.get("phase"),
            "trend":          trend,
            "has_bos":        has_bos,
            "reason":         f"Wyckoff:{wyckoff.get('phase')} Trend:{trend} BOS:{has_bos}",
        }

    # ─── Momentum Filter ─────────────────────────────────────────────────────

    def detect_momentum(self, df: pd.DataFrame) -> dict:
        """
        فلتر الزخم — يكشف الحركات المؤسسية الحقيقية

        1. Candle Expansion: range > ATR×1.5 → حركة مؤسسية
        2. Consecutive candles: 2-3+ شموع متتالية → استمرارية
        3. Displacement: body > 70% من range → دفع حقيقي بدون wick
        """
        if len(df) < 5:
            return {"strength": "WEAK", "score": 0, "consecutive_direction": "NEUTRAL"}

        atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else float((df["high"] - df["low"]).mean())
        if atr <= 0:
            atr = float((df["high"] - df["low"]).mean())

        last5 = df.tail(5)
        last_c = last5.iloc[-1]

        # 1. Candle Expansion
        c_range = float(last_c["high"]) - float(last_c["low"])
        exp_ratio = c_range / atr if atr > 0 else 0
        is_expanded = exp_ratio >= 1.5

        # 2. Consecutive same-direction (آخر 3 شموع)
        last3 = last5.tail(3)
        bull_n = sum(1 for _, r in last3.iterrows() if float(r["close"]) > float(r["open"]))
        bear_n = sum(1 for _, r in last3.iterrows() if float(r["close"]) < float(r["open"]))
        consecutive = max(bull_n, bear_n)
        consecutive_dir = "BULLISH" if bull_n >= bear_n else "BEARISH"

        # 3. Displacement
        body = abs(float(last_c["close"]) - float(last_c["open"]))
        body_ratio = body / c_range if c_range > 0 else 0
        is_displacement = body_ratio >= 0.70 and exp_ratio >= 1.2

        score = 0
        if is_expanded:       score += 40
        if consecutive >= 2:  score += 30
        if consecutive >= 3:  score += 10
        if is_displacement:   score += 30
        score = min(100, score)

        strength = "STRONG" if score >= 70 else "MODERATE" if score >= 40 else "WEAK"

        return {
            "score":                 score,
            "strength":              strength,
            "is_expanded":           is_expanded,
            "expansion_ratio":       round(exp_ratio, 2),
            "consecutive_candles":   consecutive,
            "consecutive_direction": consecutive_dir,
            "is_displacement":       is_displacement,
            "body_ratio":            round(body_ratio, 2),
        }

    # ─── Range Conflict Detection ────────────────────────────────────────────

    def detect_range_conflict(self, order_blocks: dict, structure: dict) -> dict:
        """
        كشف Range Trap: OBs صاعدة وهابطة متداخلة + لا BOS → لا دخول
        """
        bullish_obs = order_blocks.get("bullish_obs", [])
        bearish_obs = order_blocks.get("bearish_obs", [])
        has_bos = bool(structure.get("last_bos"))
        trend = (structure.get("trend") or "SIDEWAYS").upper()

        overlap = False
        overlap_details = []
        for bob in bullish_obs[:2]:
            for bearob in bearish_obs[:2]:
                b_hi, b_lo = bob.get("high", 0), bob.get("low", 0)
                r_hi, r_lo = bearob.get("high", 0), bearob.get("low", 0)
                if b_lo < r_hi and r_lo < b_hi:
                    overlap = True
                    overlap_details.append(f"Bullish[{b_lo:.2f}-{b_hi:.2f}] ∩ Bearish[{r_lo:.2f}-{r_hi:.2f}]")

        avoid_entry = overlap and not has_bos and trend == "SIDEWAYS"

        return {
            "in_range_trap":   avoid_entry,
            "has_ob_overlap":  overlap,
            "has_bos":         has_bos,
            "avoid_entry":     avoid_entry,
            "overlap_details": overlap_details[:2],
            "reason":          "تداخل OBs بدون BOS واضح — سوق Range" if avoid_entry else "لا تعارض",
        }

    # ─── Full Analysis ────────────────────────────────────────────────────────

    def full_analysis(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """التحليل الشامل - يجمع كل المكونات"""
        try:
            logger.info(f"🔍 ICT Analysis: {symbol} {timeframe}")

            structure = self.analyze_market_structure(df)
            order_blocks = self.detect_order_blocks(df)
            fvg = self.detect_fvg(df)
            liquidity = self.detect_liquidity_pools(df)

            # ── Sweep / Stop Hunt Detection (يُضاف داخل liquidity dict) ──────
            sweep_analysis = self.detect_liquidity_sweeps(df, liquidity)
            liquidity["sweep_analysis"] = sweep_analysis

            premium_discount = self.analyze_premium_discount(df)
            kill_zone = self.get_kill_zone()
            wyckoff = self.analyze_wyckoff(df)

            confluence = self.calculate_confluence(
                structure, order_blocks, fvg, liquidity,
                premium_discount, kill_zone, wyckoff, df
            )

            # ── الإضافات الجديدة ────────────────────────────────────────────
            market_mode    = self.detect_market_mode(df, wyckoff, structure)
            momentum       = self.detect_momentum(df)
            range_conflict = self.detect_range_conflict(order_blocks, structure)

            levels = {}
            if confluence["direction"] in ["BUY", "SELL"]:
                levels = self.calculate_levels(
                    df, confluence["direction"],
                    order_blocks, fvg, liquidity
                )

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                "current_price": float(df["close"].iloc[-1]),
                "atr": float(df["atr"].iloc[-1]) if "atr" in df.columns else 0,

                # المكونات
                "market_structure": structure,
                "order_blocks": order_blocks,
                "fvg": fvg,
                "liquidity": liquidity,
                "liquidity_sweep": sweep_analysis,   # مباشر للـ AI Engine
                "premium_discount": premium_discount,
                "kill_zone": kill_zone,
                "wyckoff": wyckoff,

                # التقييم
                "confluence": confluence,
                "levels": levels,

                # للـ AI Engine
                "ai_confidence_score": confluence["confidence"],
                "recommendation": confluence["direction"],
                "signal_type": confluence["quality"] if confluence["direction"] != "WAIT" else "WATCH",
                "entry_zones": [levels.get("entry", 0)] if levels else [],
                "stop_loss_zone": levels.get("stop_loss", 0),
                "take_profit_zones": [levels.get("tp1", 0), levels.get("tp2", 0), levels.get("tp3", 0)] if levels else [],
                "risk_reward_ratio": levels.get("risk_reward", 0),

                # وضع السوق والزخم
                "market_mode":    market_mode,
                "momentum":       momentum,
                "range_conflict": range_conflict,

                # المؤشرات
                "indicators": {
                    "rsi": round(float(df["rsi"].iloc[-1]), 1) if "rsi" in df.columns else 0,
                    "macd": round(float(df["macd"].iloc[-1]), 5) if "macd" in df.columns else 0,
                    "macd_signal": round(float(df["macd_signal"].iloc[-1]), 5) if "macd_signal" in df.columns else 0,
                    "ema_20": round(float(df["ema_20"].iloc[-1]), 5) if "ema_20" in df.columns else 0,
                    "ema_50": round(float(df["ema_50"].iloc[-1]), 5) if "ema_50" in df.columns else 0,
                    "stoch_k": round(float(df["stoch_k"].iloc[-1]), 1) if "stoch_k" in df.columns else 0,
                    "stoch_d": round(float(df["stoch_d"].iloc[-1]), 1) if "stoch_d" in df.columns else 0,
                }
            }

        except Exception as e:
            logger.error(f"❌ ICT Engine error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "ai_confidence_score": 0,
                "recommendation": "WAIT"
            }


# Singleton
ict_engine = ICTEngine()
