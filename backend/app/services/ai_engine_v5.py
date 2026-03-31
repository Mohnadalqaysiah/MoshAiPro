"""
Mosh AI Pro v5 - Master AI Engine (Professional Edition v2)
===========================================================
يجمع:
- SmartDataProvider (yfinance + TwelveData)
- ICT Engine (Order Blocks, FVG, BOS, Liquidity, Wyckoff)
- Gemini AI v2 (Multi-Timeframe HTF+LTF + Position Sizing)
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from app.services.smart_data import smart_data
from app.services.ict_engine import ict_engine
from app.services.gemini_engine import gemini_engine
from app.config import get_settings

settings = get_settings()

# مدة الكاش بالثواني حسب الإطار الزمني
# مُخفَّضة: المستويات تصبح قديمة بسرعة للأسواق المتحركة كالذهب
_SIGNAL_CACHE_TTL = {
    "15m":   3 * 60,   # 3 دقائق
    "30m":   5 * 60,   # 5 دقائق
    "1h":   10 * 60,   # 10 دقائق
    "4h":   20 * 60,   # 20 دقيقة (كان 90 — خُفِّض لأن الذهب يتحرك $30+ في ساعة)
    "1d":   90 * 60,   # 90 دقيقة
}

# نسبة تغير السعر التي تُلغي الكاش — مُشدَّدة لمنع إرسال مستويات قديمة
_CACHE_PRICE_DRIFT = {
    "15m": 0.002,   # 0.2%
    "30m": 0.003,   # 0.3%
    "1h":  0.004,   # 0.4%
    "4h":  0.005,   # 0.5% (كان 1.5% — خُفِّض: $3000 ذهب × 0.5% = $15 فرق مقبول)
    "1d":  0.015,   # 1.5%
}


class MoshAIEngineV5:
    """
    المحرك الرئيسي الموحّد v2

    Pipeline:
    1. جلب البيانات: 4H (HTF) + 1H (LTF) بالتوازي
    2. ICT Analysis على كلا الإطارين
    3. Gemini AI v2: يرى HTF+LTF + يحسب Position Sizing
    4. القرار النهائي مع Weighted Scoring
    """

    def __init__(self):
        self.version = "5.2.0"
        # Signal cache: key → (analysis_dict, timestamp)
        self._signal_cache: Dict[str, tuple] = {}
        logger.info(f"🚀 Mosh AI Engine v{self.version} initialized")
        logger.info(f"   └─ Gemini v2: {'✅' if gemini_engine.enabled else '❌'}")

    # ─── Cache ──────────────────────────────────────────────────────────────

    def _cache_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol.upper()}_{timeframe.lower()}"

    def _get_cached(self, symbol: str, timeframe: str, current_price: float = None) -> Optional[Dict]:
        key = self._cache_key(symbol, timeframe)
        if key not in self._signal_cache:
            return None
        data, ts = self._signal_cache[key]
        ttl = _SIGNAL_CACHE_TTL.get(timeframe, 1200)
        age = int(time.time() - ts)

        # انتهى TTL؟
        if age >= ttl:
            del self._signal_cache[key]
            return None

        # تغير السعر كثيراً؟ → ألغِ الكاش
        if current_price and data.get("current_price"):
            cached_price = float(data["current_price"])
            drift_limit = _CACHE_PRICE_DRIFT.get(timeframe, 0.008)
            drift = abs(current_price - cached_price) / cached_price
            if drift > drift_limit:
                logger.info(
                    f"🔄 Cache invalidated: {symbol}/{timeframe} "
                    f"سعر تغير {drift*100:.2f}% (حد: {drift_limit*100:.1f}%)"
                )
                del self._signal_cache[key]
                return None

        logger.info(f"📦 Signal cache hit: {symbol}/{timeframe} (عمره: {age}ث)")
        return dict(data)

    def _set_cached(self, symbol: str, timeframe: str, analysis: Dict):
        key = self._cache_key(symbol, timeframe)
        self._signal_cache[key] = (dict(analysis), time.time())

    def clear_cache(self, symbol: str = None, timeframe: str = None):
        if symbol and timeframe:
            self._signal_cache.pop(self._cache_key(symbol, timeframe), None)
        else:
            self._signal_cache.clear()
        logger.info(f"🗑️ Signal cache cleared: {symbol or 'ALL'}")

    # ─── Main Analysis ──────────────────────────────────────────────────────

    async def analyze_market(
        self,
        symbol: str,
        timeframe: str = "1h",
        advanced_mode: bool = True,
        force_refresh: bool = False,
        account_balance: float = 10000.0,
        max_risk_percent: float = 1.5,
    ) -> Dict:
        """
        التحليل الشامل للسوق v2 — HTF+LTF + Position Sizing

        Args:
            symbol: رمز السوق (XAUUSD, BTCUSD, EURUSD...)
            timeframe: الإطار الزمني LTF (1h, 4h...)
            force_refresh: تجاهل الكاش وإعادة التحليل
            account_balance: رأس مال الحساب لحساب حجم الصفقة
            max_risk_percent: نسبة المخاطرة القصوى
        """
        # ── الكاش: فحص أولي مع تحديث السعر الفوري دائماً ────────────────────
        if not force_refresh:
            # جلب السعر الحالي السريع للمقارنة مع الكاش
            live_price_meta = smart_data.get_realtime_price_with_meta(symbol)
            quick_price = live_price_meta["price"] if live_price_meta else None
            cached = self._get_cached(symbol, timeframe, current_price=quick_price)
            if cached is not None:
                # ⚡ تحديث السعر الحالي دائماً حتى من الكاش — هذا يمنع إظهار سعر قديم
                if quick_price:
                    cached["current_price"]    = quick_price
                    cached["price_source"]     = live_price_meta.get("source", "cached")
                    cached["price_fetched_at"] = live_price_meta.get("fetched_at", "")

                # تحقق: هل تجاوز السعر الحالي منطقة الدخول؟ → أبطل الكاش
                rec    = cached.get("recommendation")
                levels = cached.get("levels", {})
                entry  = float(levels.get("entry") or levels.get("entry_zone_max") or 0)
                if quick_price and entry and rec in ("BUY", "SELL"):
                    overshoot = (quick_price - entry) / entry
                    if (rec == "BUY"  and overshoot >  0.003) or \
                       (rec == "SELL" and overshoot < -0.003):
                        logger.info(
                            f"⚠️  Entry overshoot detected {symbol}/{timeframe}: "
                            f"current={quick_price:.5f} entry={entry:.5f} "
                            f"drift={overshoot*100:+.2f}% — إعادة التحليل"
                        )
                        self._signal_cache.pop(self._cache_key(symbol, timeframe), None)
                        # fall through to fresh analysis
                    else:
                        cached["from_cache"] = True
                        return cached
                else:
                    cached["from_cache"] = True
                    return cached

        logger.info(f"📊 Starting analysis v2: {symbol} / {timeframe}")
        start = datetime.now()

        try:
            # ── Step 1: جلب LTF + HTF بالتوازي ─────────────────────────────
            htf_timeframe = "4h" if timeframe in ("1h", "15m", "30m") else "1d"

            df_ltf, df_htf = await asyncio.gather(
                smart_data.get_ohlcv(symbol, timeframe, bars=150),
                smart_data.get_ohlcv(symbol, htf_timeframe, bars=100),
            )

            if df_ltf is None or len(df_ltf) < 30:
                logger.error(f"❌ No LTF data for {symbol}")
                return self._error_response(symbol, "لا توجد بيانات كافية")

            logger.info(
                f"   ✅ LTF ({timeframe}): {len(df_ltf)} bars, "
                f"price={df_ltf['close'].iloc[-1]:.5f}"
            )
            if df_htf is not None:
                logger.info(f"   ✅ HTF ({htf_timeframe}): {len(df_htf)} bars")

            # ── Step 2: ICT Analysis على LTF + HTF ──────────────────────────
            ltf_analysis = ict_engine.full_analysis(df_ltf, symbol, timeframe)

            htf_analysis = None
            if df_htf is not None and len(df_htf) >= 30:
                htf_analysis = ict_engine.full_analysis(df_htf, symbol, htf_timeframe)

            if "error" in ltf_analysis:
                return self._error_response(symbol, ltf_analysis["error"])

            # ── Step 3: Gemini v2 Enhancement ───────────────────────────────
            if gemini_engine.enabled:
                try:
                    gemini_result = await gemini_engine.analyze(
                        symbol=symbol,
                        timeframe=timeframe,
                        ltf_data=ltf_analysis,
                        df=df_ltf,
                        htf_data=htf_analysis,
                        account_balance=account_balance,
                        max_risk_percent=max_risk_percent,
                    )
                    if gemini_result:
                        ltf_analysis = gemini_engine.merge_with_ict(ltf_analysis, gemini_result)
                        sig = gemini_result.get("signal", {})
                        logger.success(
                            f"   🤖 Gemini v2: {sig.get('recommendation')} | "
                            f"Grade: {sig.get('signal_grade')} | "
                            f"Score: {gemini_result.get('scoring_breakdown', {}).get('total', 0)}/100"
                        )
                except Exception as e:
                    logger.warning(f"   ⚠️ Gemini v2 failed (using ICT only): {e}")

            # ── Step 4: Final formatting ─────────────────────────────────────
            ms = (datetime.now() - start).total_seconds() * 1000
            analysis = ltf_analysis
            analysis["processing_time_ms"] = int(ms)
            analysis["version"] = self.version
            analysis["market_open"] = smart_data.is_market_open(symbol)
            analysis["htf_timeframe"] = htf_timeframe

            # HTF context للمنصة والبوت
            if htf_analysis:
                analysis["htf_context"] = {
                    "timeframe": htf_timeframe,
                    "trend": htf_analysis.get("market_structure", {}).get("trend", "UNKNOWN"),
                    "structure": htf_analysis.get("market_structure", {}).get("structure", "UNKNOWN"),
                    "premium_discount": htf_analysis.get("premium_discount", {}).get("zone", "UNKNOWN"),
                    "wyckoff_phase": htf_analysis.get("wyckoff", {}).get("phase", "UNKNOWN"),
                }

            # توافق مع API القديم
            analysis["trend"] = {
                "direction": analysis.get("market_structure", {}).get("trend", "RANGING"),
                "strength": analysis.get("ai_confidence_score", 0),
                "htf_trend": analysis.get("htf_context", {}).get("trend", "UNKNOWN"),
            }

            # ── بوابة السيولة الذكية (Smart Money Gate) ──────────────────────
            analysis = self._validate_sweep_gate(analysis)

            # ── التحقق الإجباري من صحة المستويات ────────────────────────────
            analysis = self._validate_trade_levels(analysis)

            rec  = analysis.get("recommendation", "WAIT")
            conf = analysis.get("ai_confidence_score", 0)
            logger.success(f"✅ {symbol}/{timeframe}: {rec} | {conf}% | {int(ms)}ms")

            # ── السعر الفوري + تصحيح Futures→Spot للمعادن والعقود الآجلة ──
            try:
                rt_price = smart_data.get_realtime_price_with_meta(symbol)
                if rt_price:
                    analysis["current_price"]    = rt_price["price"]
                    analysis["price_source"]     = rt_price["source"]
                    analysis["price_fetched_at"] = rt_price["fetched_at"]
                    logger.info(f"   💱 Live price [{rt_price['source']}]: {rt_price['price']}")

                    # ── تصحيح Futures-Spot لأسواق المعادن والعقود ──────────
                    # المشكلة: مستويات ICT محسوبة من بيانات GC=F (Futures)
                    # بينما المتداول يرى سعر XAUUSD Spot في MT4/MT5
                    # الحل: جلب Spot من Finnhub وتطبيق الفارق على كل المستويات
                    analysis = self._apply_spot_basis(symbol, analysis)

            except Exception as _pe:
                logger.warning(f"   ⚠️ Could not fetch live price: {_pe}")

            # ── حفظ في الكاش ─────────────────────────────────────────────
            analysis["from_cache"] = False
            analysis["cached_at"] = datetime.now().isoformat()
            analysis["cache_ttl_seconds"] = _SIGNAL_CACHE_TTL.get(timeframe, 1800)
            self._set_cached(symbol, timeframe, analysis)

            return analysis

        except Exception as e:
            logger.error(f"❌ Engine error for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(symbol, str(e))

    # الأسواق التي تستخدم Futures في yfinance (GC=F, SI=F ...)
    _FUTURES_SPOT_SYMBOLS = {"XAUUSD", "XAGUSD"}

    def _apply_spot_basis(self, symbol: str, analysis: dict) -> dict:
        """
        يُصحِّح فارق Futures-Spot لأسواق المعادن.
        GC=F (ذهب futures) دائماً أعلى من XAUUSD spot بـ $10-40.
        نطرح هذا الفارق من كل المستويات ليتطابق مع ما يراه المتداول في MT4/MT5.
        """
        if symbol.upper() not in self._FUTURES_SPOT_SYMBOLS:
            return analysis
        if not smart_data._fh_key:
            return analysis

        try:
            import requests as _req
            from app.services.smart_data import FINNHUB_MAP
            fh_sym = FINNHUB_MAP.get(symbol.upper())
            if not fh_sym:
                return analysis

            resp = _req.get(
                f"{smart_data._fh_base}/quote",
                params={"symbol": fh_sym, "token": smart_data._fh_key},
                timeout=4,
            )
            spot = float((resp.json().get("c") or resp.json().get("l")) or 0)
            if spot <= 0:
                return analysis

            futures = float(analysis.get("current_price") or 0)
            if futures <= 0:
                return analysis

            basis = spot - futures  # عادةً سالب: spot أقل من futures

            # sanity check: الفارق يجب أن يكون معقولاً (0.01% – 3%)
            ratio = abs(basis) / futures
            if ratio < 0.0001 or ratio > 0.03:
                logger.debug(f"   ⚠️  Basis out of range for {symbol}: {basis:+.2f} ({ratio*100:.2f}%) — skipped")
                return analysis

            logger.info(f"   🔧 Spot-Futures basis [{symbol}]: {basis:+.2f}  (futures={futures:.2f} → spot={spot:.2f})")

            # ── تطبيق الفارق على current_price ───────────────────────────
            analysis["current_price"]  = round(spot, 5)
            analysis["price_source"]   = "finnhub_spot"
            analysis["futures_basis"]  = round(basis, 2)

            def _shift(v):
                return round(float(v) + basis, 5) if v else v

            # ── المستويات الرئيسية (levels dict) ─────────────────────────
            lvls = analysis.get("levels", {})
            for k in ("entry", "entry_zone_min", "entry_zone_max", "stop_loss", "tp1", "tp2"):
                if lvls.get(k):
                    lvls[k] = _shift(lvls[k])

            # ── entry_zones / stop_loss_zone / take_profit_zones (legacy) ─
            if analysis.get("entry_zones"):
                analysis["entry_zones"] = [_shift(z) for z in analysis["entry_zones"] if z]
            if analysis.get("stop_loss_zone"):
                analysis["stop_loss_zone"] = _shift(analysis["stop_loss_zone"])
            if analysis.get("take_profit_zones"):
                analysis["take_profit_zones"] = [_shift(z) for z in analysis["take_profit_zones"] if z]

            # ── Order Blocks ──────────────────────────────────────────────
            ob = analysis.get("order_blocks", {})
            for ob_list in (ob.get("bullish_obs", []), ob.get("bearish_obs", [])):
                for o in ob_list:
                    if isinstance(o, dict):
                        for k in ("low", "high", "mid"):
                            if o.get(k):
                                o[k] = _shift(o[k])

            # ── Liquidity levels ──────────────────────────────────────────
            liq = analysis.get("liquidity_analysis") or analysis.get("liquidity") or {}
            if isinstance(liq, dict):
                for k in ("nearest_ssl", "nearest_bsl"):
                    if liq.get(k):
                        liq[k] = _shift(liq[k])
                bias = liq.get("bias", {})
                if isinstance(bias, dict):
                    for k in ("below_price", "above_price"):
                        if bias.get(k):
                            bias[k] = _shift(bias[k])

        except Exception as e:
            logger.warning(f"   ⚠️  _apply_spot_basis failed for {symbol}: {e}")

        return analysis

    def _validate_sweep_gate(self, analysis: dict) -> dict:
        """
        بوابة السيولة الصارمة — ICT Hard Gate (شرط قاطع لا استثناء)

        مبدأ: الصفقة تُمنع كلياً ما لم يُكتشف Stop Hunt مؤكد:
            ✅ sweep + rejection_confirmed → يُسمح بالدخول
            ❌ sweep بدون rejection       → WAIT فوري
            ❌ لا sweep على الإطلاق       → WAIT فوري
        """
        rec = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return analysis

        # جلب بيانات الـ Sweep من ICT أو من Liquidity dict
        sweep = (
            analysis.get("liquidity_sweep")
            or analysis.get("liquidity", {}).get("sweep_analysis")
            or {}
        )

        has_confirmed_sweep = (
            sweep.get("has_bullish_sweep") if rec == "BUY"
            else sweep.get("has_bearish_sweep")
        )

        # ✅ الحالة الوحيدة المسموح بها: Sweep + Rejection مؤكد
        if has_confirmed_sweep:
            sweep_quality = sweep.get("sweep_quality", "MODERATE")
            logger.debug(f"✅ Sweep Gate PASSED [{rec}]: quality={sweep_quality}")
            return analysis

        # ─── كل الحالات الأخرى → WAIT فوري ───────────────────────────────────

        # تحديد السبب الدقيق للرفض
        has_any_sweep = (
            bool(sweep.get("ssl_sweep")) if rec == "BUY"
            else bool(sweep.get("bsl_sweep"))
        )

        if has_any_sweep:
            reason = "اكتساح سيولة بدون رفض مؤكد (Sweep ≠ Rejection)"
            short  = "SWEEP_NO_REJECTION"
        else:
            reason = "لم يُكتشف اكتساح سيولة (شرط ICT الأساسي غير متحقق)"
            short  = "NO_SWEEP"

        logger.warning(
            f"🚫 Sweep Hard Gate BLOCKED [{rec}] → WAIT | reason={short} | "
            f"has_bullish={sweep.get('has_bullish_sweep')} "
            f"has_bearish={sweep.get('has_bearish_sweep')}"
        )

        # تحويل إجباري لـ WAIT
        analysis["recommendation"]    = "WAIT"
        analysis["ai_confidence_score"] = min(
            float(analysis.get("ai_confidence_score") or 0), 54.0
        )

        # تسجيل السبب في الـ factors
        conf_data = analysis.get("confluence", {})
        if isinstance(conf_data, dict):
            factors = conf_data.get("factors", [])
            if isinstance(factors, list):
                factors.insert(0, f"🚫 Sweep Gate: {reason}")

        # حقل مستقل لسهولة الـ debugging
        analysis["sweep_gate_blocked"] = True
        analysis["sweep_gate_reason"]  = short

        # مسح مستويات الدخول المرفوضة — لا نعرض SL/TP من إشارة محظورة
        # (تجنب عرض مستويات SELL مقلوبة عند تحويل التوصية إلى WAIT)
        analysis["levels"] = {}
        analysis["entry_zones"] = []
        analysis["stop_loss_zone"] = None
        analysis["take_profit_zones"] = []

        return analysis

    def _validate_trade_levels(self, analysis: dict) -> dict:
        """
        تحقق إجباري: SL أسفل entry وTP فوق entry للشراء، والعكس للبيع.
        إذا فشل → يُحوَّل لـ WAIT تلقائياً.
        """
        rec    = analysis.get("recommendation")
        levels = analysis.get("levels", {})
        if rec not in ("BUY", "SELL") or not levels:
            return analysis

        entry = float(levels.get("entry") or 0)
        sl    = float(levels.get("stop_loss") or 0)
        tp1   = float(levels.get("tp1") or 0)
        if not entry or not sl or not tp1:
            return analysis

        if rec == "BUY":
            valid = sl < entry < tp1
        else:
            valid = tp1 < entry < sl

        if not valid:
            logger.warning(
                f"⛔ Trade Validation FAILED [{rec}]: "
                f"entry={entry} sl={sl} tp1={tp1} → تحويل إلى WAIT"
            )
            analysis["recommendation"] = "WAIT"
            analysis["ai_confidence_score"] = min(
                float(analysis.get("ai_confidence_score") or 0), 55.0
            )
        return analysis

    def _error_response(self, symbol: str, error: str) -> Dict:
        return {
            "symbol": symbol,
            "error": error,
            "ai_confidence_score": 0,
            "recommendation": "WAIT",
            "signal_type": "ERROR",
            "entry_zones": [],
            "stop_loss_zone": 0,
            "take_profit_zones": [],
            "risk_reward_ratio": 0,
            "timestamp": datetime.now().isoformat(),
        }


# Singleton
mosh_ai_engine_v5 = MoshAIEngineV5()
