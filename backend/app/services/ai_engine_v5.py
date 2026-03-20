"""
Mosh AI Pro v5 - Main AI Engine
Integrates all analysis components into unified intelligent system
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from app.services.data_provider import data_provider
from app.services.rate_limiter import twelvedata_client
from app.services.premium_discount import premium_discount_engine
from app.services.wyckoff_engine import wyckoff_engine
from app.services.liquidity_engine_v2 import liquidity_engine_v2
from app.services.volume_intelligence_v2 import volume_intelligence_v2
from app.services.killzones_engine import killzones_engine
from app.services.bos_analyzer import bos_analyzer
from app.services.breaker_blocks import breaker_blocks_detector
from app.services.gemini_engine import gemini_engine
from app.config import get_settings

settings = get_settings()


class MoshAIEngineV5:
    """
    Master AI Engine integrating all advanced strategies:
    - Wyckoff Cycles
    - Premium/Discount Zones
    - Equal Highs/Lows Liquidity
    - Volume Intelligence
    - Killzones Timing
    - BOS Analysis
    - Breaker Blocks
    - Time & Price Theory
    """
    
    def __init__(self):
        self.version = "5.0.0"
        logger.info(f"🚀 Mosh AI Engine v{self.version} initialized")
    
    async def analyze_market(
        self,
        symbol: str,
        timeframe: str = "1h",
        advanced_mode: bool = True
    ) -> Dict:
        """
        Perform comprehensive market analysis
        
        Args:
            symbol: Market symbol (e.g., 'XAUUSD')
            timeframe: Analysis timeframe
            advanced_mode: Enable all advanced features
        
        Returns:
            Complete analysis dictionary
        """
        
        logger.info(f"🔍 Starting analysis for {symbol} on {timeframe}")
        start_time = datetime.now()
        
        try:
            # Step 1: Fetch market data (Smart Rate Limiter + Cache)
            df = await twelvedata_client.get_ohlcv(symbol, timeframe, outputsize=100)
            
            if df is None or len(df) < 50:
                logger.error(f"❌ Insufficient data for {symbol}")
                return self._empty_analysis()
            
            current_price = float(df["close"].iloc[-1])
            atr = data_provider.calculate_atr(df).iloc[-1]  # still use helper for ATR calc
            
            # Step 2: Core Analysis Components
            
            # Premium/Discount Zones
            premium_discount = premium_discount_engine.analyze(df) if settings.ENABLE_PREMIUM_DISCOUNT else {}
            
            # Wyckoff Cycle Analysis
            wyckoff = wyckoff_engine.analyze(df) if settings.ENABLE_WYCKOFF_ANALYSIS else {}
            
            # Advanced Liquidity Analysis
            liquidity = liquidity_engine_v2.analyze(df) if settings.ENABLE_LIQUIDITY_ENGINE else {}
            
            # Volume Intelligence
            volume = volume_intelligence_v2.analyze(df) if settings.ENABLE_VOLUME_INTELLIGENCE else {}
            
            # Killzones Timing
            killzones = killzones_engine.analyze() if settings.ENABLE_KILLZONES else {}
            
            # BOS Analysis
            bos = bos_analyzer.analyze(df) if advanced_mode else {}
            
            # Breaker Blocks
            breaker_blocks = breaker_blocks_detector.analyze(df) if settings.ENABLE_BREAKER_BLOCKS else {}
            
            # Step 3: Trend Detection
            trend = self._detect_trend(df, bos)
            
            # Step 4: Market Structure
            market_structure = self._analyze_market_structure(df)
            
            # Step 5: Calculate AI Confidence Score
            ai_score = self._calculate_ai_score(
                premium_discount,
                wyckoff,
                liquidity,
                volume,
                killzones,
                bos,
                trend
            )
            
            # Step 6: Generate Trading Decision
            decision = self._generate_decision(
                ai_score,
                trend,
                premium_discount,
                wyckoff,
                liquidity,
                killzones
            )
            
            # Step 7: Build Complete Analysis
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            analysis = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                "processing_time_ms": int(processing_time),
                
                # Price Info
                "current_price": current_price,
                "atr": float(atr),
                
                # Trend & Structure
                "trend": trend,
                "market_structure": market_structure,
                
                # AI Score
                "ai_confidence_score": ai_score,
                "score_breakdown": self._get_score_breakdown(
                    premium_discount, wyckoff, liquidity, volume, killzones, bos
                ),
                
                # Components
                "premium_discount": premium_discount,
                "wyckoff_analysis": wyckoff,
                "liquidity_analysis": liquidity,
                "volume_analysis": volume,
                "killzones": killzones,
                "bos_analysis": bos,
                "breaker_blocks": breaker_blocks,
                
                # Decision
                "recommendation": decision["action"],
                "signal_type": decision["signal_type"],
                "entry_zones": decision["entry_zones"],
                "stop_loss_zone": decision["stop_loss"],
                "take_profit_zones": decision["take_profits"],
                "risk_reward_ratio": decision["risk_reward"],
                
                # Metadata
                "version": self.version,
                "advanced_mode": advanced_mode
            }
            
            logger.success(f"✅ Analysis complete: Score={ai_score}, Signal={decision['signal_type']}")

            # Step 8: Gemini AI Enhancement (إذا مفعّل)
            if gemini_engine.enabled:
                try:
                    gemini_result = await gemini_engine.analyze(symbol, timeframe, analysis)
                    analysis = gemini_engine.merge_with_technical(analysis, gemini_result)
                    logger.success(f"🤖 Gemini enhanced: Score={analysis['ai_confidence_score']}, Signal={analysis['recommendation']}")
                except Exception as ge:
                    logger.warning(f"⚠️ Gemini enhancement failed (using technical only): {ge}")

            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return self._empty_analysis()
    
    def _detect_trend(self, df: pd.DataFrame, bos: Dict) -> Dict:
        """Detect market trend using multiple confirmations"""
        
        # Use BOS trend if available
        if bos and "current_trend" in bos:
            bos_trend = bos["current_trend"]
        else:
            bos_trend = "RANGING"
        
        # Moving averages
        ma_20 = df["close"].rolling(20).mean().iloc[-1]
        ma_50 = df["close"].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma_20
        current_price = df["close"].iloc[-1]
        
        # Price above both MAs = uptrend
        if current_price > ma_20 > ma_50:
            ma_trend = "BULLISH"
        elif current_price < ma_20 < ma_50:
            ma_trend = "BEARISH"
        else:
            ma_trend = "RANGING"
        
        # Higher highs / lower lows
        recent_highs = df["high"].tail(20)
        recent_lows = df["low"].tail(20)
        
        hh = recent_highs.iloc[-1] > recent_highs.iloc[-10]
        hl = recent_lows.iloc[-1] > recent_lows.iloc[-10]
        
        if hh and hl:
            structure_trend = "BULLISH"
        elif not hh and not hl:
            structure_trend = "BEARISH"
        else:
            structure_trend = "RANGING"
        
        # Final trend (majority vote)
        trends = [bos_trend, ma_trend, structure_trend]
        bullish_count = trends.count("BULLISH")
        bearish_count = trends.count("BEARISH")
        
        if bullish_count >= 2:
            final_trend = "BULLISH"
            strength = 80 if bullish_count == 3 else 65
        elif bearish_count >= 2:
            final_trend = "BEARISH"
            strength = 80 if bearish_count == 3 else 65
        else:
            final_trend = "RANGING"
            strength = 50
        
        return {
            "direction": final_trend,
            "strength": strength,
            "confirmations": {
                "bos": bos_trend,
                "moving_averages": ma_trend,
                "structure": structure_trend
            }
        }
    
    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """Analyze market structure (HH, HL, LH, LL)"""
        
        recent = df.tail(30)
        
        # Find swing points
        highs = []
        lows = []
        
        for i in range(5, len(recent) - 5):
            # Swing high
            if all(recent["high"].iloc[i] > recent["high"].iloc[i-j] for j in range(1, 6)) and \
               all(recent["high"].iloc[i] > recent["high"].iloc[i+j] for j in range(1, 6)):
                highs.append(recent["high"].iloc[i])
            
            # Swing low
            if all(recent["low"].iloc[i] < recent["low"].iloc[i-j] for j in range(1, 6)) and \
               all(recent["low"].iloc[i] < recent["low"].iloc[i+j] for j in range(1, 6)):
                lows.append(recent["low"].iloc[i])
        
        structure = "UNKNOWN"
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Higher Highs and Higher Lows = Bullish
            if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
                structure = "HH_HL"
            # Lower Highs and Lower Lows = Bearish
            elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
                structure = "LH_LL"
            else:
                structure = "MIXED"
        
        return {
            "pattern": structure,
            "swing_highs": [float(h) for h in highs[-3:]] if highs else [],
            "swing_lows": [float(l) for l in lows[-3:]] if lows else []
        }
    
    def _calculate_ai_score(
        self,
        premium_discount: Dict,
        wyckoff: Dict,
        liquidity: Dict,
        volume: Dict,
        killzones: Dict,
        bos: Dict,
        trend: Dict
    ) -> float:
        """
        Calculate overall AI confidence score (0-100)
        Weighted combination of all components
        """
        
        score = 0.0
        weights = {
            "premium_discount": 0.20,
            "wyckoff": 0.20,
            "liquidity": 0.20,
            "volume": 0.10,
            "killzones": 0.10,
            "bos": 0.10,
            "trend": 0.10
        }
        
        # Premium/Discount contribution
        if premium_discount and "confidence" in premium_discount:
            score += premium_discount["confidence"] * weights["premium_discount"]
        
        # Wyckoff contribution
        if wyckoff and "confidence" in wyckoff:
            score += wyckoff["confidence"] * weights["wyckoff"]
        
        # Liquidity contribution
        if liquidity and "confidence" in liquidity:
            score += liquidity["confidence"] * weights["liquidity"]
        
        # Volume contribution
        if volume and "confidence" in volume:
            score += volume["confidence"] * weights["volume"]
        
        # Killzones contribution
        if killzones and "confidence" in killzones:
            score += killzones["confidence"] * weights["killzones"]
        
        # BOS contribution
        if bos and "confidence" in bos:
            score += bos["confidence"] * weights["bos"]
        
        # Trend contribution
        if trend and "strength" in trend:
            score += trend["strength"] * weights["trend"]
        
        return round(score, 2)
    
    def _get_score_breakdown(
        self,
        premium_discount,
        wyckoff,
        liquidity,
        volume,
        killzones,
        bos
    ) -> Dict:
        """Get detailed score breakdown"""
        
        return {
            "premium_discount": premium_discount.get("confidence", 0) if premium_discount else 0,
            "wyckoff": wyckoff.get("confidence", 0) if wyckoff else 0,
            "liquidity": liquidity.get("confidence", 0) if liquidity else 0,
            "volume": volume.get("confidence", 0) if volume else 0,
            "killzones": killzones.get("confidence", 0) if killzones else 0,
            "bos": bos.get("confidence", 0) if bos else 0
        }
    
    def _generate_decision(
        self,
        ai_score: float,
        trend: Dict,
        premium_discount: Dict,
        wyckoff: Dict,
        liquidity: Dict,
        killzones: Dict
    ) -> Dict:
        """Generate trading decision based on analysis"""
        
        # Default: WAIT
        if ai_score < settings.AI_CONFIDENCE_THRESHOLD:
            return self._wait_decision()
        
        # Determine signal type
        trend_dir = trend.get("direction", "RANGING")
        pd_zone = premium_discount.get("current_zone", "UNKNOWN") if premium_discount else "UNKNOWN"
        wyckoff_action = wyckoff.get("action", "WAIT") if wyckoff else "WAIT"
        liq_bias = liquidity.get("bias", {}).get("direction", "NEUTRAL") if liquidity else "NEUTRAL"
        kz_optimal = killzones.get("is_optimal_time", False) if killzones else False
        
        # BUY conditions
        if (trend_dir == "BULLISH" and 
            pd_zone in ["DISCOUNT", "EXTREME_DISCOUNT", "EQUILIBRIUM"] and
            liq_bias in ["BULLISH", "NEUTRAL"] and
            wyckoff_action in ["PREPARE_BUY", "BUY_SIGNAL", "HOLD_LONG"]):
            
            signal_type = "BUY"
            quality = "PREMIUM" if ai_score >= settings.PREMIUM_CONFIDENCE_THRESHOLD and kz_optimal else "STANDARD"
        
        # SELL conditions
        elif (trend_dir == "BEARISH" and
              pd_zone in ["PREMIUM", "EXTREME_PREMIUM", "EQUILIBRIUM"] and
              liq_bias in ["BEARISH", "NEUTRAL"] and
              wyckoff_action in ["PREPARE_SELL", "SELL_SIGNAL", "HOLD_SHORT"]):
            
            signal_type = "SELL"
            quality = "PREMIUM" if ai_score >= settings.PREMIUM_CONFIDENCE_THRESHOLD and kz_optimal else "STANDARD"
        
        else:
            return self._watch_decision()
        
        # Generate entry/SL/TP (simplified - would be more complex in production)
        current_price = premium_discount.get("price_levels", {}).get("current", 0) if premium_discount else 0
        
        if signal_type == "BUY":
            entry = current_price
            sl = entry - (entry * 0.01)  # 1% SL
            tp1 = entry + (entry * 0.015)  # 1.5% TP1
            tp2 = entry + (entry * 0.025)  # 2.5% TP2
        else:  # SELL
            entry = current_price
            sl = entry + (entry * 0.01)
            tp1 = entry - (entry * 0.015)
            tp2 = entry - (entry * 0.025)
        
        risk_reward = abs(tp2 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
        
        return {
            "action": signal_type,
            "signal_type": signal_type,
            "quality": quality,
            "entry_zones": [entry],
            "stop_loss": sl,
            "take_profits": [tp1, tp2],
            "risk_reward": round(risk_reward, 2)
        }
    
    def _wait_decision(self) -> Dict:
        return {
            "action": "WAIT",
            "signal_type": "WATCH",
            "quality": "NONE",
            "entry_zones": [],
            "stop_loss": 0,
            "take_profits": [],
            "risk_reward": 0
        }
    
    def _watch_decision(self) -> Dict:
        return {
            "action": "WATCH",
            "signal_type": "WATCH",
            "quality": "STANDARD",
            "entry_zones": [],
            "stop_loss": 0,
            "take_profits": [],
            "risk_reward": 0
        }
    
    def _empty_analysis(self) -> Dict:
        return {
            "error": "Analysis failed",
            "ai_confidence_score": 0,
            "recommendation": "WAIT"
        }


# Singleton instance
mosh_ai_engine_v5 = MoshAIEngineV5()
