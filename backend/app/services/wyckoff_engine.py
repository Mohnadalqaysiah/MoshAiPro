"""
Mosh AI Pro v5 - Wyckoff Cycles Engine
Detects market phases: Accumulation, Markup, Distribution, Markdown
Based on Wyckoff Method principles
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger


class WyckoffEngine:
    """
    Analyzes market cycles using Wyckoff methodology:
    - Phase 1: Accumulation (Smart Money buying)
    - Phase 2: Markup (Price rising)
    - Phase 3: Distribution (Smart Money selling)
    - Phase 4: Markdown (Price falling)
    
    Also detects key events: Spring, Upthrust, Test, Sign of Strength (SOS), etc.
    """
    
    def __init__(self, lookback_period: int = 100):
        """
        Args:
            lookback_period: Number of candles to analyze
        """
        self.lookback_period = lookback_period
    
    def analyze(self, df: pd.DataFrame, volume_data: Optional[Dict] = None) -> Dict:
        """
        Perform Wyckoff cycle analysis
        
        Args:
            df: DataFrame with OHLC data
            volume_data: Optional volume analysis data
        
        Returns:
            Dictionary with Wyckoff analysis
        """
        if df is None or len(df) < 50:
            return self._empty_result()
        
        try:
            recent_df = df.tail(self.lookback_period).copy()
            
            # Detect current phase
            phase = self._detect_phase(recent_df, volume_data)
            
            # Detect Wyckoff events
            events = self._detect_events(recent_df, volume_data)
            
            # Calculate phase strength
            phase_strength = self._calculate_phase_strength(recent_df, phase, events)
            
            # Determine trading action
            action = self._determine_action(phase, events, phase_strength)
            
            # Calculate confidence
            confidence = self._calculate_confidence(phase, events, phase_strength)
            
            result = {
                "phase": phase,
                "phase_strength": phase_strength,
                "phase_description": self._get_phase_description(phase),
                "events": events,
                "action": action,
                "confidence": confidence,
                "characteristics": self._get_phase_characteristics(phase),
                "next_expected_phase": self._get_next_phase(phase),
                "time_in_phase": self._estimate_time_in_phase(recent_df, phase)
            }
            
            logger.info(f"📊 Wyckoff Phase: {phase} (Strength: {phase_strength}%) - Action: {action}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Wyckoff analysis: {e}")
            return self._empty_result()
    
    def _detect_phase(self, df: pd.DataFrame, volume_data: Optional[Dict]) -> str:
        """Detect current Wyckoff phase"""
        
        # Calculate trend metrics
        recent_highs = df["high"].tail(20)
        recent_lows = df["low"].tail(20)
        current_price = df["close"].iloc[-1]
        
        # Calculate moving averages for trend
        ma_20 = df["close"].rolling(20).mean().iloc[-1]
        ma_50 = df["close"].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma_20
        
        # Price position relative to range
        price_range = recent_highs.max() - recent_lows.min()
        if price_range == 0:
            return "RANGING"
        
        price_position = (current_price - recent_lows.min()) / price_range
        
        # Trend direction
        is_uptrend = ma_20 > ma_50 if len(df) >= 50 else df["close"].iloc[-1] > df["close"].iloc[-20]
        is_downtrend = ma_20 < ma_50 if len(df) >= 50 else df["close"].iloc[-1] < df["close"].iloc[-20]
        
        # Volume analysis (if available)
        volume_increasing = False
        if volume_data:
            volume_trend = volume_data.get("volume_trend", "STABLE")
            volume_increasing = volume_trend == "INCREASING"
        
        # Volatility (using ATR proxy)
        volatility = df["high"].tail(20) - df["low"].tail(20)
        avg_volatility = volatility.mean()
        current_volatility = volatility.iloc[-1]
        
        is_low_volatility = current_volatility < (avg_volatility * 0.7)
        is_high_volatility = current_volatility > (avg_volatility * 1.3)
        
        # Phase detection logic
        if is_low_volatility and not is_uptrend and not is_downtrend:
            # Low volatility + sideways = Accumulation or Distribution
            if price_position < 0.5:
                return "ACCUMULATION"
            else:
                return "DISTRIBUTION"
        
        elif is_uptrend and volume_increasing:
            return "MARKUP"
        
        elif is_downtrend and volume_increasing:
            return "MARKDOWN"
        
        elif is_low_volatility and price_position < 0.4:
            return "ACCUMULATION"
        
        elif is_low_volatility and price_position > 0.6:
            return "DISTRIBUTION"
        
        elif is_uptrend:
            return "MARKUP"
        
        elif is_downtrend:
            return "MARKDOWN"
        
        else:
            return "RANGING"
    
    def _detect_events(self, df: pd.DataFrame, volume_data: Optional[Dict]) -> List[Dict]:
        """Detect Wyckoff events (Spring, Upthrust, Test, etc.)"""
        
        events = []
        
        recent = df.tail(30)
        
        # Detect Spring (fake breakdown then reversal up)
        spring_detected = self._detect_spring(recent)
        if spring_detected:
            events.append({
                "type": "SPRING",
                "description": "Bullish reversal after false breakdown",
                "significance": "HIGH",
                "timeframe": "Recent"
            })
        
        # Detect Upthrust (fake breakout then reversal down)
        upthrust_detected = self._detect_upthrust(recent)
        if upthrust_detected:
            events.append({
                "type": "UPTHRUST",
                "description": "Bearish reversal after false breakout",
                "significance": "HIGH",
                "timeframe": "Recent"
            })
        
        # Detect Sign of Strength (SOS)
        sos_detected = self._detect_sos(recent)
        if sos_detected:
            events.append({
                "type": "SIGN_OF_STRENGTH",
                "description": "Strong bullish momentum",
                "significance": "MEDIUM",
                "timeframe": "Recent"
            })
        
        # Detect Sign of Weakness (SOW)
        sow_detected = self._detect_sow(recent)
        if sow_detected:
            events.append({
                "type": "SIGN_OF_WEAKNESS",
                "description": "Strong bearish momentum",
                "significance": "MEDIUM",
                "timeframe": "Recent"
            })
        
        return events
    
    def _detect_spring(self, df: pd.DataFrame) -> bool:
        """Detect Spring pattern"""
        if len(df) < 10:
            return False
        
        # Look for: new low, then strong reversal up
        recent_low = df["low"].min()
        last_close = df["close"].iloc[-1]
        
        # Check if price made new low then recovered above recent lows
        low_idx = df["low"].idxmin()
        if low_idx < len(df) - 5:  # Low was not too recent
            recovery = (last_close - recent_low) / recent_low
            if recovery > 0.005:  # 0.5% recovery
                return True
        
        return False
    
    def _detect_upthrust(self, df: pd.DataFrame) -> bool:
        """Detect Upthrust pattern"""
        if len(df) < 10:
            return False
        
        # Look for: new high, then strong reversal down
        recent_high = df["high"].max()
        last_close = df["close"].iloc[-1]
        
        # Check if price made new high then dropped below recent highs
        high_idx = df["high"].idxmax()
        if high_idx < len(df) - 5:
            drop = (recent_high - last_close) / recent_high
            if drop > 0.005:
                return True
        
        return False
    
    def _detect_sos(self, df: pd.DataFrame) -> bool:
        """Detect Sign of Strength"""
        if len(df) < 5:
            return False
        
        # Look for strong bullish candles
        last_5 = df.tail(5)
        bullish_count = (last_5["close"] > last_5["open"]).sum()
        
        # Strong upward momentum
        price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]
        
        return bullish_count >= 4 and price_change > 0.01
    
    def _detect_sow(self, df: pd.DataFrame) -> bool:
        """Detect Sign of Weakness"""
        if len(df) < 5:
            return False
        
        # Look for strong bearish candles
        last_5 = df.tail(5)
        bearish_count = (last_5["close"] < last_5["open"]).sum()
        
        # Strong downward momentum
        price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]
        
        return bearish_count >= 4 and price_change < -0.01
    
    def _calculate_phase_strength(self, df: pd.DataFrame, phase: str, events: List) -> float:
        """Calculate strength of current phase (0-100)"""
        
        strength = 50.0  # Base strength
        
        # Adjust based on events
        for event in events:
            if event["significance"] == "HIGH":
                strength += 15
            elif event["significance"] == "MEDIUM":
                strength += 10
        
        # Adjust based on phase characteristics
        if phase in ["ACCUMULATION", "DISTRIBUTION"]:
            # Check for consolidation
            volatility = (df["high"].tail(20) - df["low"].tail(20)).mean()
            avg_volatility = (df["high"] - df["low"]).mean()
            if volatility < avg_volatility * 0.8:
                strength += 10
        
        elif phase in ["MARKUP", "MARKDOWN"]:
            # Check for trend strength
            sma_20 = df["close"].rolling(20).mean().iloc[-1]
            current_price = df["close"].iloc[-1]
            distance = abs(current_price - sma_20) / sma_20
            strength += min(distance * 1000, 20)  # Cap at +20
        
        return min(max(strength, 0), 100)
    
    def _determine_action(self, phase: str, events: List, strength: float) -> str:
        """Determine recommended trading action"""
        
        actions = {
            "ACCUMULATION": "PREPARE_BUY",
            "MARKUP": "HOLD_LONG",
            "DISTRIBUTION": "PREPARE_SELL",
            "MARKDOWN": "HOLD_SHORT",
            "RANGING": "WAIT"
        }
        
        base_action = actions.get(phase, "WAIT")
        
        # Modify based on events
        for event in events:
            if event["type"] == "SPRING":
                return "BUY_SIGNAL"
            elif event["type"] == "UPTHRUST":
                return "SELL_SIGNAL"
        
        return base_action
    
    def _calculate_confidence(self, phase: str, events: List, strength: float) -> float:
        """Calculate overall confidence score"""
        
        base_confidence = {
            "ACCUMULATION": 70,
            "MARKUP": 80,
            "DISTRIBUTION": 70,
            "MARKDOWN": 80,
            "RANGING": 40
        }
        
        confidence = base_confidence.get(phase, 50)
        
        # Boost for detected events
        if events:
            confidence += len(events) * 5
        
        # Adjust for strength
        confidence = confidence * (strength / 100)
        
        return min(confidence, 100)
    
    def _get_phase_description(self, phase: str) -> str:
        """Get human-readable phase description"""
        descriptions = {
            "ACCUMULATION": "Smart Money is accumulating (buying quietly)",
            "MARKUP": "Price is rising (bullish trend active)",
            "DISTRIBUTION": "Smart Money is distributing (selling quietly)",
            "MARKDOWN": "Price is falling (bearish trend active)",
            "RANGING": "Market is consolidating (no clear direction)"
        }
        return descriptions.get(phase, "Unknown phase")
    
    def _get_phase_characteristics(self, phase: str) -> List[str]:
        """Get characteristics of current phase"""
        characteristics = {
            "ACCUMULATION": [
                "Low volatility",
                "Sideways price action",
                "Smart money buying",
                "Public uninterested"
            ],
            "MARKUP": [
                "Rising prices",
                "Higher highs and higher lows",
                "Increasing momentum",
                "Public FOMO buying"
            ],
            "DISTRIBUTION": [
                "Low volatility at top",
                "Sideways after uptrend",
                "Smart money selling",
                "Public most bullish"
            ],
            "MARKDOWN": [
                "Falling prices",
                "Lower highs and lower lows",
                "Increasing selling pressure",
                "Public panic selling"
            ],
            "RANGING": [
                "No clear direction",
                "Choppy price action",
                "Low conviction"
            ]
        }
        return characteristics.get(phase, [])
    
    def _get_next_phase(self, current_phase: str) -> str:
        """Predict next phase"""
        transitions = {
            "ACCUMULATION": "MARKUP",
            "MARKUP": "DISTRIBUTION",
            "DISTRIBUTION": "MARKDOWN",
            "MARKDOWN": "ACCUMULATION",
            "RANGING": "ACCUMULATION or DISTRIBUTION"
        }
        return transitions.get(current_phase, "Unknown")
    
    def _estimate_time_in_phase(self, df: pd.DataFrame, phase: str) -> str:
        """Estimate how long market has been in this phase"""
        # Simplified estimation
        return "Recent"
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "phase": "UNKNOWN",
            "phase_strength": 0,
            "phase_description": "",
            "events": [],
            "action": "WAIT",
            "confidence": 0,
            "characteristics": [],
            "next_expected_phase": "",
            "time_in_phase": ""
        }


# Singleton instance
wyckoff_engine = WyckoffEngine()
