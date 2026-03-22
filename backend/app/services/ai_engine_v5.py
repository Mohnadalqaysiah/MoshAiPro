"""
Mosh AI Pro v5 - Master AI Engine (Professional Edition)
=========================================================
يجمع:
- SmartDataProvider (yfinance + TwelveData)
- ICT Engine (Order Blocks, FVG, BOS, Liquidity, Wyckoff)
- Gemini AI (التحليل النهائي بخبرة 15 سنة)
"""

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
    "15m":  10 * 60,   # 10 دقائق
    "1h":   30 * 60,   # 30 دقيقة
    "4h":  120 * 60,   # ساعتان
    "1d":  360 * 60,   # 6 ساعات
}


class MoshAIEngineV5:
    """
    المحرك الرئيسي الموحّد

    Pipeline:
    1. جلب البيانات (yfinance → TwelveData fallback)
    2. حساب المؤشرات التقنية
    3. تحليل ICT الكامل (OB, FVG, BOS, Liquidity, PD, KZ, Wyckoff)
    4. حساب Confluence Score
    5. Gemini AI Enhancement
    6. القرار النهائي
    """

    def __init__(self):
        self.version = "5.1.0"
        # Signal cache: key → (analysis_dict, timestamp)
        self._signal_cache: Dict[str, tuple] = {}
        logger.info(f"🚀 Mosh AI Engine v{self.version} initialized")
        logger.info(f"   └─ Gemini: {'✅' if gemini_engine.enabled else '❌'}")

    def _cache_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol.upper()}_{timeframe.lower()}"

    def _get_cached(self, symbol: str, timeframe: str) -> Optional[Dict]:
        key = self._cache_key(symbol, timeframe)
        if key not in self._signal_cache:
            return None
        data, ts = self._signal_cache[key]
        ttl = _SIGNAL_CACHE_TTL.get(timeframe, 1800)
        age = int(time.time() - ts)
        if age < ttl:
            logger.info(f"📦 Signal cache hit: {symbol}/{timeframe} (عمره: {age}ث)")
            return dict(data)  # نسخة لتجنب التعديل المشترك
        del self._signal_cache[key]
        return None

    def _set_cached(self, symbol: str, timeframe: str, analysis: Dict):
        key = self._cache_key(symbol, timeframe)
        self._signal_cache[key] = (dict(analysis), time.time())

    def clear_cache(self, symbol: str = None, timeframe: str = None):
        """مسح الكاش — كامل أو لزوج محدد"""
        if symbol and timeframe:
            self._signal_cache.pop(self._cache_key(symbol, timeframe), None)
        else:
            self._signal_cache.clear()
        logger.info(f"🗑️ Signal cache cleared: {symbol or 'ALL'}")

    async def analyze_market(
        self,
        symbol: str,
        timeframe: str = "1h",
        advanced_mode: bool = True,
        force_refresh: bool = False
    ) -> Dict:
        """
        التحليل الشامل للسوق

        Args:
            symbol: رمز السوق (XAUUSD, BTCUSD, EURUSD...)
            timeframe: الإطار الزمني (15m, 1h, 4h, 1d)
            force_refresh: تجاهل الكاش وإعادة التحليل

        Returns:
            Dict كامل بكل التحليل والتوصيات
        """
        # ── الكاش: إذا توجد نتيجة حديثة → أرجعها مباشرة ──────────────────
        if not force_refresh:
            cached = self._get_cached(symbol, timeframe)
            if cached is not None:
                cached["from_cache"] = True
                return cached

        logger.info(f"📊 Starting analysis: {symbol} / {timeframe}")
        start = datetime.now()

        try:
            # ── Step 1: جلب البيانات ──────────────────────────────────────────
            df = await smart_data.get_ohlcv(symbol, timeframe, bars=150)

            if df is None or len(df) < 30:
                logger.error(f"❌ No data for {symbol}")
                return self._error_response(symbol, "لا توجد بيانات كافية")

            logger.info(f"   ✅ Data: {len(df)} bars, price={df['close'].iloc[-1]:.5f}")

            # ── Step 2: ICT Analysis الكامل ─────────────────────────────────
            analysis = ict_engine.full_analysis(df, symbol, timeframe)

            if "error" in analysis:
                return self._error_response(symbol, analysis["error"])

            # ── Step 3: Gemini Enhancement ───────────────────────────────────
            if gemini_engine.enabled:
                try:
                    gemini_result = await gemini_engine.analyze(
                        symbol, timeframe, analysis, df
                    )
                    if gemini_result:
                        analysis = gemini_engine.merge_with_ict(analysis, gemini_result)
                        logger.success(
                            f"   🤖 Gemini: {analysis['recommendation']} "
                            f"({analysis['ai_confidence_score']}%)"
                        )
                except Exception as e:
                    logger.warning(f"   ⚠️ Gemini failed (using ICT only): {e}")

            # ── Step 4: Final formatting ─────────────────────────────────────
            ms = (datetime.now() - start).total_seconds() * 1000
            analysis["processing_time_ms"] = int(ms)
            analysis["version"] = self.version
            analysis["market_open"] = smart_data.is_market_open(symbol)

            # Map old fields for API compatibility
            analysis["trend"] = {
                "direction": analysis.get("market_structure", {}).get("trend", "RANGING"),
                "strength": analysis.get("ai_confidence_score", 0),
                "confirmations": {
                    "structure": analysis.get("market_structure", {}).get("structure", "UNKNOWN"),
                    "bos": analysis.get("market_structure", {}).get("trend", "RANGING"),
                }
            }
            analysis["score_breakdown"] = {
                "market_structure": analysis.get("market_structure", {}).get("confidence", 0),
                "order_blocks": 25 if analysis.get("order_blocks", {}).get("in_bullish_ob") or
                                      analysis.get("order_blocks", {}).get("in_bearish_ob") else 0,
                "fvg": 15 if analysis.get("fvg", {}).get("in_bullish_fvg") or
                            analysis.get("fvg", {}).get("in_bearish_fvg") else 0,
                "premium_discount": analysis.get("premium_discount", {}).get("confidence", 0),
                "kill_zone": analysis.get("kill_zone", {}).get("confidence", 0),
                "wyckoff": analysis.get("wyckoff", {}).get("confidence", 0),
            }

            rec = analysis.get("recommendation", "WAIT")
            conf = analysis.get("ai_confidence_score", 0)
            logger.success(f"✅ {symbol}/{timeframe}: {rec} | {conf}% | {int(ms)}ms")

            # ── حفظ في الكاش ─────────────────────────────────────────────
            analysis["from_cache"] = False
            analysis["cached_at"] = datetime.now().isoformat()
            ttl = _SIGNAL_CACHE_TTL.get(timeframe, 1800)
            analysis["cache_ttl_seconds"] = ttl
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
