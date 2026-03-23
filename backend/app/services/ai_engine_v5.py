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
_SIGNAL_CACHE_TTL = {
    "15m":   3 * 60,   # 3 دقائق فقط (السوق يتغير سريعاً)
    "30m":   8 * 60,   # 8 دقائق
    "1h":   20 * 60,   # 20 دقيقة
    "4h":   90 * 60,   # 90 دقيقة
    "1d":  300 * 60,   # 5 ساعات
}

# نسبة تغير السعر التي تُلغي الكاش (0.3% = 0.003)
_CACHE_PRICE_DRIFT = {
    "15m": 0.003,   # 0.3%
    "30m": 0.005,   # 0.5%
    "1h":  0.008,   # 0.8%
    "4h":  0.015,   # 1.5%
    "1d":  0.030,   # 3%
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
        # ── الكاش: فحص أولي بدون سعر ─────────────────────────────────────────
        if not force_refresh:
            # جلب السعر الحالي السريع للمقارنة مع الكاش
            quick_price = smart_data.get_current_price(symbol)
            cached = self._get_cached(symbol, timeframe, current_price=quick_price)
            if cached is not None:
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

            rec  = analysis.get("recommendation", "WAIT")
            conf = analysis.get("ai_confidence_score", 0)
            logger.success(f"✅ {symbol}/{timeframe}: {rec} | {conf}% | {int(ms)}ms")

            # ── السعر الفوري الحقيقي (TwelveData spot أو yfinance 1m) ──────
            try:
                rt_price = smart_data.get_realtime_price_with_meta(symbol)
                if rt_price:
                    analysis["current_price"]   = rt_price["price"]
                    analysis["price_source"]    = rt_price["source"]
                    analysis["price_fetched_at"] = rt_price["fetched_at"]
                    logger.info(f"   💱 Live price [{rt_price['source']}]: {rt_price['price']}")
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
