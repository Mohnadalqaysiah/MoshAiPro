"""
Mosh AI Pro v5 - Advanced Liquidity Engine v2
Detects Equal Highs, Equal Lows, Liquidity Pools, and Liquidity Sweeps
Based on Smart Money Concepts (SMC)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from loguru import logger


class LiquidityEngineV2:
    """
    Advanced liquidity analysis detecting:
    - Equal Highs (multiple highs at same level = liquidity pool)
    - Equal Lows (multiple lows at same level = liquidity pool)
    - Liquidity Pools (zones with clustered stop losses)
    - Liquidity Grabs/Sweeps (when price hunts stops then reverses)
    - External Liquidity (major levels outside recent range)
    """
    
    def __init__(self, tolerance: float = 0.002):
        """
        Args:
            tolerance: Price tolerance for equal levels (0.2% default)
        """
        self.tolerance = tolerance
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform comprehensive liquidity analysis
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dictionary with liquidity analysis
        """
        if df is None or len(df) < 30:
            return self._empty_result()
        
        try:
            # Detect equal highs and lows
            equal_highs = self._detect_equal_highs(df)
            equal_lows = self._detect_equal_lows(df)
            
            # Detect liquidity pools
            liquidity_pools = self._detect_liquidity_pools(df, equal_highs, equal_lows)
            
            # Detect recent liquidity grabs
            liquidity_grabs = self._detect_liquidity_grabs(df, equal_highs, equal_lows)
            
            # Identify external liquidity
            external_liquidity = self._identify_external_liquidity(df)
            
            # Calculate liquidity score
            liquidity_score = self._calculate_liquidity_score(
                equal_highs, equal_lows, liquidity_pools, liquidity_grabs
            )
            
            # Determine trading bias based on liquidity
            bias = self._determine_liquidity_bias(
                df, equal_highs, equal_lows, liquidity_grabs
            )
            
            result = {
                "equal_highs": equal_highs,
                "equal_lows": equal_lows,
                "liquidity_pools": liquidity_pools,
                "liquidity_grabs": liquidity_grabs,
                "external_liquidity": external_liquidity,
                "liquidity_score": liquidity_score,
                "bias": bias,
                "confidence": self._calculate_confidence(equal_highs, equal_lows, liquidity_grabs)
            }
            
            logger.info(f"💧 Liquidity: {len(equal_highs)} EQHs, {len(equal_lows)} EQLs, "
                       f"{len(liquidity_grabs)} recent grabs")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Liquidity analysis: {e}")
            return self._empty_result()
    
    def _detect_equal_highs(self, df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """
        Detect Equal Highs (EQH) - multiple swing highs at same level
        This indicates buy-side liquidity (stops above these highs)
        """
        equal_highs = []
        
        # Find swing highs
        swing_highs = self._find_swing_highs(df.tail(lookback))
        
        if len(swing_highs) < 2:
            return equal_highs
        
        # Group similar highs
        for i, (idx1, high1) in enumerate(swing_highs):
            matching_highs = [(idx1, high1)]
            
            for idx2, high2 in swing_highs[i+1:]:
                if abs(high1 - high2) / high1 <= self.tolerance:
                    matching_highs.append((idx2, high2))
            
            # If we found at least 2 equal highs
            if len(matching_highs) >= 2:
                avg_level = np.mean([h for _, h in matching_highs])
                
                equal_highs.append({
                    "level": float(avg_level),
                    "count": len(matching_highs),
                    "strength": min(len(matching_highs) * 30, 100),
                    "type": "EQUAL_HIGH",
                    "description": f"{len(matching_highs)} equal highs forming buy-side liquidity",
                    "target_probability": "HIGH" if len(matching_highs) >= 3 else "MEDIUM"
                })
                
                # Remove used swing highs to avoid duplication
                swing_highs = [(idx, h) for idx, h in swing_highs 
                              if (idx, h) not in matching_highs]
        
        return equal_highs
    
    def _detect_equal_lows(self, df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """
        Detect Equal Lows (EQL) - multiple swing lows at same level
        This indicates sell-side liquidity (stops below these lows)
        """
        equal_lows = []
        
        # Find swing lows
        swing_lows = self._find_swing_lows(df.tail(lookback))
        
        if len(swing_lows) < 2:
            return equal_lows
        
        # Group similar lows
        for i, (idx1, low1) in enumerate(swing_lows):
            matching_lows = [(idx1, low1)]
            
            for idx2, low2 in swing_lows[i+1:]:
                if abs(low1 - low2) / low1 <= self.tolerance:
                    matching_lows.append((idx2, low2))
            
            # If we found at least 2 equal lows
            if len(matching_lows) >= 2:
                avg_level = np.mean([l for _, l in matching_lows])
                
                equal_lows.append({
                    "level": float(avg_level),
                    "count": len(matching_lows),
                    "strength": min(len(matching_lows) * 30, 100),
                    "type": "EQUAL_LOW",
                    "description": f"{len(matching_lows)} equal lows forming sell-side liquidity",
                    "target_probability": "HIGH" if len(matching_lows) >= 3 else "MEDIUM"
                })
                
                # Remove used swing lows
                swing_lows = [(idx, l) for idx, l in swing_lows 
                             if (idx, l) not in matching_lows]
        
        return equal_lows
    
    def _find_swing_highs(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """Find swing high points"""
        swing_highs = []
        
        for i in range(window, len(df) - window):
            current_high = df["high"].iloc[i]
            
            # Check if this is a swing high
            left_check = all(current_high > df["high"].iloc[i-j] for j in range(1, window+1))
            right_check = all(current_high > df["high"].iloc[i+j] for j in range(1, window+1))
            
            if left_check and right_check:
                swing_highs.append((i, current_high))
        
        return swing_highs
    
    def _find_swing_lows(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """Find swing low points"""
        swing_lows = []
        
        for i in range(window, len(df) - window):
            current_low = df["low"].iloc[i]
            
            # Check if this is a swing low
            left_check = all(current_low < df["low"].iloc[i-j] for j in range(1, window+1))
            right_check = all(current_low < df["low"].iloc[i+j] for j in range(1, window+1))
            
            if left_check and right_check:
                swing_lows.append((i, current_low))
        
        return swing_lows
    
    def _detect_liquidity_pools(
        self, 
        df: pd.DataFrame, 
        equal_highs: List[Dict], 
        equal_lows: List[Dict]
    ) -> List[Dict]:
        """
        Detect liquidity pools (zones with concentrated liquidity)
        """
        pools = []
        
        # Convert equal highs to pools
        for eq_high in equal_highs:
            pools.append({
                "type": "BUY_SIDE_LIQUIDITY",
                "level": eq_high["level"],
                "strength": eq_high["strength"],
                "description": "Stops clustered above equal highs",
                "expected_action": "Price likely to sweep these stops"
            })
        
        # Convert equal lows to pools
        for eq_low in equal_lows:
            pools.append({
                "type": "SELL_SIDE_LIQUIDITY",
                "level": eq_low["level"],
                "strength": eq_low["strength"],
                "description": "Stops clustered below equal lows",
                "expected_action": "Price likely to sweep these stops"
            })
        
        return pools
    
    def _detect_liquidity_grabs(
        self, 
        df: pd.DataFrame, 
        equal_highs: List[Dict], 
        equal_lows: List[Dict]
    ) -> List[Dict]:
        """
        Detect recent liquidity grabs/sweeps
        (Price briefly breaks a level to trigger stops, then reverses)
        """
        grabs = []
        recent = df.tail(20)
        
        # Check for sweeps above equal highs
        for eq_high in equal_highs:
            level = eq_high["level"]
            
            # Look for wicks above the level followed by rejection
            for i in range(len(recent) - 1):
                if recent["high"].iloc[i] > level and recent["close"].iloc[i] < level:
                    # Wick above, close below = potential grab
                    if recent["close"].iloc[i+1] < level:
                        grabs.append({
                            "type": "BUY_SIDE_GRAB",
                            "level": float(level),
                            "direction": "BEARISH",
                            "description": "Swept buy-side liquidity, expect downside",
                            "significance": "HIGH",
                            "candles_ago": len(recent) - i - 1
                        })
                        break
        
        # Check for sweeps below equal lows
        for eq_low in equal_lows:
            level = eq_low["level"]
            
            # Look for wicks below the level followed by rejection
            for i in range(len(recent) - 1):
                if recent["low"].iloc[i] < level and recent["close"].iloc[i] > level:
                    # Wick below, close above = potential grab
                    if recent["close"].iloc[i+1] > level:
                        grabs.append({
                            "type": "SELL_SIDE_GRAB",
                            "level": float(level),
                            "direction": "BULLISH",
                            "description": "Swept sell-side liquidity, expect upside",
                            "significance": "HIGH",
                            "candles_ago": len(recent) - i - 1
                        })
                        break
        
        return grabs
    
    def _identify_external_liquidity(self, df: pd.DataFrame) -> Dict:
        """
        Identify major external liquidity (levels outside recent range)
        """
        recent = df.tail(100)
        current_high = recent["high"].max()
        current_low = recent["low"].min()
        
        # Look for significant levels in historical data
        historical = df.tail(200) if len(df) >= 200 else df
        
        # Find major highs above current range
        above_range_highs = historical[historical["high"] > current_high * 1.01]["high"].values
        
        # Find major lows below current range
        below_range_lows = historical[historical["low"] < current_low * 0.99]["low"].values
        
        return {
            "above_range": {
                "levels": [float(h) for h in above_range_highs[:5]] if len(above_range_highs) > 0 else [],
                "description": "Major resistance with buy-side liquidity"
            },
            "below_range": {
                "levels": [float(l) for l in below_range_lows[:5]] if len(below_range_lows) > 0 else [],
                "description": "Major support with sell-side liquidity"
            }
        }
    
    def _calculate_liquidity_score(
        self,
        equal_highs: List,
        equal_lows: List,
        liquidity_pools: List,
        liquidity_grabs: List
    ) -> float:
        """Calculate overall liquidity score (0-100)"""
        
        score = 50.0  # Base score
        
        # Add points for equal highs/lows
        score += len(equal_highs) * 10
        score += len(equal_lows) * 10
        
        # Add points for recent grabs (strong signal)
        score += len(liquidity_grabs) * 15
        
        return min(score, 100)
    
    def _determine_liquidity_bias(
        self,
        df: pd.DataFrame,
        equal_highs: List,
        equal_lows: List,
        liquidity_grabs: List
    ) -> Dict:
        """Determine trading bias based on liquidity"""
        
        current_price = df["close"].iloc[-1]
        
        # Find closest liquidity levels
        closest_high = min(equal_highs, key=lambda x: abs(x["level"] - current_price)) if equal_highs else None
        closest_low = min(equal_lows, key=lambda x: abs(x["level"] - current_price)) if equal_lows else None
        
        # Check recent grabs
        recent_bullish_grab = any(g["direction"] == "BULLISH" for g in liquidity_grabs if g["candles_ago"] < 10)
        recent_bearish_grab = any(g["direction"] == "BEARISH" for g in liquidity_grabs if g["candles_ago"] < 10)
        
        # Determine bias
        if recent_bullish_grab:
            return {
                "direction": "BULLISH",
                "strength": 80,
                "reason": "Recent sell-side liquidity grab indicates upside"
            }
        elif recent_bearish_grab:
            return {
                "direction": "BEARISH",
                "strength": 80,
                "reason": "Recent buy-side liquidity grab indicates downside"
            }
        elif closest_high and closest_low:
            dist_to_high = abs(current_price - closest_high["level"])
            dist_to_low = abs(current_price - closest_low["level"])
            
            if dist_to_high < dist_to_low:
                return {
                    "direction": "BULLISH",
                    "strength": 60,
                    "reason": "Closer to buy-side liquidity above"
                }
            else:
                return {
                    "direction": "BEARISH",
                    "strength": 60,
                    "reason": "Closer to sell-side liquidity below"
                }
        else:
            return {
                "direction": "NEUTRAL",
                "strength": 50,
                "reason": "No clear liquidity bias"
            }
    
    def _calculate_confidence(
        self,
        equal_highs: List,
        equal_lows: List,
        liquidity_grabs: List
    ) -> float:
        """Calculate confidence in liquidity analysis"""
        
        confidence = 50.0
        
        # Boost for detected patterns
        confidence += len(equal_highs) * 10
        confidence += len(equal_lows) * 10
        confidence += len(liquidity_grabs) * 15
        
        return min(confidence, 100)
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "equal_highs": [],
            "equal_lows": [],
            "liquidity_pools": [],
            "liquidity_grabs": [],
            "external_liquidity": {},
            "liquidity_score": 0,
            "bias": {"direction": "NEUTRAL", "strength": 0, "reason": ""},
            "confidence": 0
        }


# Singleton instance
liquidity_engine_v2 = LiquidityEngineV2()
