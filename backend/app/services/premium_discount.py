"""
Mosh AI Pro v5 - Premium/Discount Zones Engine
Analyzes if price is in premium (expensive) or discount (cheap) zones
Based on 50% Fibonacci principle from Smart Money Concepts
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger


class PremiumDiscountEngine:
    """
    Determines if current price is in:
    - Premium Zone (upper 50% - expensive, good for sells)
    - Discount Zone (lower 50% - cheap, good for buys)
    - Equilibrium (around 50% - neutral)
    """
    
    def __init__(self, lookback_period: int = 100):
        """
        Args:
            lookback_period: Number of candles to calculate range
        """
        self.lookback_period = lookback_period
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze premium/discount zones
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dictionary with premium/discount analysis
        """
        if df is None or len(df) < self.lookback_period:
            return self._empty_result()
        
        try:
            # Get recent data
            recent_df = df.tail(self.lookback_period).copy()
            
            # Calculate swing high and low
            swing_high = recent_df["high"].max()
            swing_low = recent_df["low"].min()
            current_price = recent_df["close"].iloc[-1]
            
            # Calculate range
            price_range = swing_high - swing_low
            
            if price_range == 0:
                return self._empty_result()
            
            # Calculate 50% level (equilibrium)
            equilibrium = swing_low + (price_range * 0.5)
            
            # Calculate Fibonacci levels
            fib_levels = {
                "0%": swing_low,
                "23.6%": swing_low + (price_range * 0.236),
                "38.2%": swing_low + (price_range * 0.382),
                "50%": equilibrium,
                "61.8%": swing_low + (price_range * 0.618),
                "78.6%": swing_low + (price_range * 0.786),
                "100%": swing_high
            }
            
            # Determine current zone
            percentage_in_range = ((current_price - swing_low) / price_range) * 100
            
            if percentage_in_range >= 70:
                current_zone = "EXTREME_PREMIUM"
                zone_strength = "VERY_STRONG"
                recommendation = "STRONG_SELL_ZONE"
            elif percentage_in_range >= 55:
                current_zone = "PREMIUM"
                zone_strength = "STRONG"
                recommendation = "SELL_ZONE"
            elif percentage_in_range >= 45:
                current_zone = "EQUILIBRIUM"
                zone_strength = "NEUTRAL"
                recommendation = "WAIT"
            elif percentage_in_range >= 30:
                current_zone = "DISCOUNT"
                zone_strength = "STRONG"
                recommendation = "BUY_ZONE"
            else:
                current_zone = "EXTREME_DISCOUNT"
                zone_strength = "VERY_STRONG"
                recommendation = "STRONG_BUY_ZONE"
            
            # Calculate zone boundaries
            premium_zone = {
                "start": equilibrium,
                "end": swing_high,
                "levels": [fib_levels["61.8%"], fib_levels["78.6%"], fib_levels["100%"]]
            }
            
            discount_zone = {
                "start": swing_low,
                "end": equilibrium,
                "levels": [fib_levels["0%"], fib_levels["23.6%"], fib_levels["38.2%"]]
            }
            
            # Distance to equilibrium
            distance_to_eq = abs(current_price - equilibrium)
            distance_to_eq_pct = (distance_to_eq / price_range) * 100
            
            # Trading bias
            if current_zone in ["EXTREME_DISCOUNT", "DISCOUNT"]:
                bias = "BULLISH"
                bias_strength = 80 if current_zone == "EXTREME_DISCOUNT" else 60
            elif current_zone in ["EXTREME_PREMIUM", "PREMIUM"]:
                bias = "BEARISH"
                bias_strength = 80 if current_zone == "EXTREME_PREMIUM" else 60
            else:
                bias = "NEUTRAL"
                bias_strength = 50
            
            result = {
                "current_zone": current_zone,
                "zone_strength": zone_strength,
                "recommendation": recommendation,
                "percentage_in_range": round(percentage_in_range, 2),
                "bias": bias,
                "bias_strength": bias_strength,
                "price_levels": {
                    "current": float(current_price),
                    "swing_high": float(swing_high),
                    "swing_low": float(swing_low),
                    "equilibrium": float(equilibrium),
                    "range": float(price_range)
                },
                "fibonacci_levels": {k: float(v) for k, v in fib_levels.items()},
                "premium_zone": {k: float(v) if isinstance(v, (int, float, np.number)) 
                                else [float(x) for x in v] for k, v in premium_zone.items()},
                "discount_zone": {k: float(v) if isinstance(v, (int, float, np.number)) 
                                 else [float(x) for x in v] for k, v in discount_zone.items()},
                "distance_to_equilibrium": {
                    "points": float(distance_to_eq),
                    "percentage": round(distance_to_eq_pct, 2)
                },
                "confidence": self._calculate_confidence(current_zone, zone_strength)
            }
            
            logger.info(f"✅ Premium/Discount: {current_zone} ({percentage_in_range:.1f}%) - {recommendation}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Premium/Discount analysis: {e}")
            return self._empty_result()
    
    def _calculate_confidence(self, zone: str, strength: str) -> float:
        """Calculate confidence score based on zone and strength"""
        base_scores = {
            "EXTREME_PREMIUM": 90,
            "PREMIUM": 75,
            "EQUILIBRIUM": 50,
            "DISCOUNT": 75,
            "EXTREME_DISCOUNT": 90
        }
        
        strength_multipliers = {
            "VERY_STRONG": 1.0,
            "STRONG": 0.9,
            "NEUTRAL": 0.7
        }
        
        base = base_scores.get(zone, 50)
        multiplier = strength_multipliers.get(strength, 0.8)
        
        return round(base * multiplier, 2)
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "current_zone": "UNKNOWN",
            "zone_strength": "UNKNOWN",
            "recommendation": "WAIT",
            "percentage_in_range": 0,
            "bias": "NEUTRAL",
            "bias_strength": 0,
            "price_levels": {},
            "fibonacci_levels": {},
            "premium_zone": {},
            "discount_zone": {},
            "distance_to_equilibrium": {},
            "confidence": 0
        }
    
    def should_allow_buy(self, analysis: Dict) -> bool:
        """
        Check if buy signals should be allowed in current zone
        
        Args:
            analysis: Premium/Discount analysis result
        
        Returns:
            True if buying is recommended
        """
        zone = analysis.get("current_zone", "UNKNOWN")
        return zone in ["DISCOUNT", "EXTREME_DISCOUNT", "EQUILIBRIUM"]
    
    def should_allow_sell(self, analysis: Dict) -> bool:
        """
        Check if sell signals should be allowed in current zone
        
        Args:
            analysis: Premium/Discount analysis result
        
        Returns:
            True if selling is recommended
        """
        zone = analysis.get("current_zone", "UNKNOWN")
        return zone in ["PREMIUM", "EXTREME_PREMIUM", "EQUILIBRIUM"]


# Singleton instance
premium_discount_engine = PremiumDiscountEngine()
