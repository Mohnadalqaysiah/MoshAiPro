"""
Mosh AI Pro v5 - BOS Analyzer
Detects Internal BOS, External BOS, and CHoCH (Change of Character)
"""

import pandas as pd
from typing import Dict, List
from loguru import logger


class BOSAnalyzer:
    """
    Analyzes Break of Structure:
    - Internal BOS: Minor structure breaks within trend
    - External BOS: Major trend reversals
    - CHoCH: Change of Character (early reversal signal)
    """
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """Perform BOS analysis"""
        
        if df is None or len(df) < 30:
            return self._empty_result()
        
        try:
            # Detect structure breaks
            internal_bos = self._detect_internal_bos(df)
            external_bos = self._detect_external_bos(df)
            choch = self._detect_choch(df)
            
            # Calculate BOS strength
            bos_strength = self._calculate_bos_strength(internal_bos, external_bos, choch)
            
            # Determine trend
            trend = self._determine_trend(internal_bos, external_bos)
            
            result = {
                "internal_bos": internal_bos,
                "external_bos": external_bos,
                "choch": choch,
                "bos_strength": bos_strength,
                "current_trend": trend,
                "confidence": 70.0
            }
            
            logger.info(f"🔀 BOS: Trend={trend}, Strength={bos_strength}%")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in BOS analysis: {e}")
            return self._empty_result()
    
    def _detect_internal_bos(self, df: pd.DataFrame) -> List[Dict]:
        """Detect internal structure breaks (minor)"""
        
        bos_events = []
        recent = df.tail(30)
        
        # Simple implementation: look for breaks of recent swing points
        highs = recent["high"]
        lows = recent["low"]
        
        recent_high = highs.tail(10).max()
        recent_low = lows.tail(10).min()
        
        current_price = recent["close"].iloc[-1]
        
        # Bullish internal BOS: break above recent high
        if current_price > recent_high:
            bos_events.append({
                "type": "INTERNAL_BULLISH",
                "level": float(recent_high),
                "description": "Minor bullish structure break"
            })
        
        # Bearish internal BOS: break below recent low
        if current_price < recent_low:
            bos_events.append({
                "type": "INTERNAL_BEARISH",
                "level": float(recent_low),
                "description": "Minor bearish structure break"
            })
        
        return bos_events
    
    def _detect_external_bos(self, df: pd.DataFrame) -> List[Dict]:
        """Detect external structure breaks (major trend changes)"""
        
        bos_events = []
        
        # Look at longer timeframe
        longer_high = df["high"].tail(50).max()
        longer_low = df["low"].tail(50).min()
        
        current_price = df["close"].iloc[-1]
        
        # Major bullish BOS
        if current_price > longer_high:
            bos_events.append({
                "type": "EXTERNAL_BULLISH",
                "level": float(longer_high),
                "description": "Major bullish trend reversal",
                "significance": "HIGH"
            })
        
        # Major bearish BOS
        if current_price < longer_low:
            bos_events.append({
                "type": "EXTERNAL_BEARISH",
                "level": float(longer_low),
                "description": "Major bearish trend reversal",
                "significance": "HIGH"
            })
        
        return bos_events
    
    def _detect_choch(self, df: pd.DataFrame) -> List[Dict]:
        """Detect Change of Character events"""
        
        choch_events = []
        
        # CHoCH = early sign of trend change
        # Look for: trend weakening, lower highs in uptrend or higher lows in downtrend
        
        recent = df.tail(20)
        highs = recent["high"]
        lows = recent["low"]
        
        # Check for lower high in recent uptrend
        if len(highs) >= 10:
            prev_high = highs.iloc[-10]
            current_high = highs.iloc[-1]
            
            if current_high < prev_high * 0.998:  # Lower high
                choch_events.append({
                    "type": "BEARISH_CHOCH",
                    "description": "Lower high detected - potential trend weakening",
                    "significance": "MEDIUM"
                })
        
        # Check for higher low in recent downtrend
        if len(lows) >= 10:
            prev_low = lows.iloc[-10]
            current_low = lows.iloc[-1]
            
            if current_low > prev_low * 1.002:  # Higher low
                choch_events.append({
                    "type": "BULLISH_CHOCH",
                    "description": "Higher low detected - potential trend weakening",
                    "significance": "MEDIUM"
                })
        
        return choch_events
    
    def _calculate_bos_strength(
        self,
        internal_bos: List,
        external_bos: List,
        choch: List
    ) -> float:
        """Calculate overall BOS strength"""
        
        strength = 50.0
        
        strength += len(internal_bos) * 10
        strength += len(external_bos) * 20
        strength += len(choch) * 15
        
        return min(strength, 100)
    
    def _determine_trend(self, internal_bos: List, external_bos: List) -> str:
        """Determine current trend based on BOS"""
        
        # Check latest BOS events
        all_bos = internal_bos + external_bos
        
        if not all_bos:
            return "RANGING"
        
        latest = all_bos[-1]
        
        if "BULLISH" in latest["type"]:
            return "BULLISH"
        elif "BEARISH" in latest["type"]:
            return "BEARISH"
        else:
            return "RANGING"
    
    def _empty_result(self) -> Dict:
        return {
            "internal_bos": [],
            "external_bos": [],
            "choch": [],
            "bos_strength": 0,
            "current_trend": "UNKNOWN",
            "confidence": 0
        }


# Singleton
bos_analyzer = BOSAnalyzer()
