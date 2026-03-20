"""
Mosh AI Pro v5 - Breaker Blocks Detector
Detects Breaker Blocks and Mitigation Blocks
Breaker Block = Failed Order Block that becomes strong reversal zone
"""

import pandas as pd
from typing import Dict, List
from loguru import logger


class BreakerBlocksDetector:
    """
    Detects:
    - Breaker Blocks: Order blocks that failed and flipped
    - Mitigation Blocks: Zones where price mitigates imbalances
    - Rejection Blocks: Strong rejection zones
    """
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """Detect breaker and mitigation blocks"""
        
        if df is None or len(df) < 40:
            return self._empty_result()
        
        try:
            # Detect breaker blocks
            breaker_blocks = self._detect_breaker_blocks(df)
            
            # Detect mitigation blocks
            mitigation_blocks = self._detect_mitigation_blocks(df)
            
            # Detect rejection blocks
            rejection_blocks = self._detect_rejection_blocks(df)
            
            result = {
                "breaker_blocks": breaker_blocks,
                "mitigation_blocks": mitigation_blocks,
                "rejection_blocks": rejection_blocks,
                "confidence": 65.0
            }
            
            logger.info(f"🔄 Breaker Blocks: {len(breaker_blocks)} detected")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Breaker Blocks analysis: {e}")
            return self._empty_result()
    
    def _detect_breaker_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect breaker blocks
        Logic: Bullish OB that got broken bearishly becomes Bearish BB
        """
        
        breaker_blocks = []
        recent = df.tail(50)
        
        # Look for strong bearish candles after bullish zones
        for i in range(10, len(recent) - 5):
            # Check for bullish candle followed by strong bearish break
            current = recent.iloc[i]
            
            if current["close"] > current["open"]:  # Bullish candle
                # Check if price came back and broke it bearishly
                for j in range(i+1, min(i+10, len(recent))):
                    future = recent.iloc[j]
                    
                    if future["close"] < current["low"]:  # Broke the bullish block
                        breaker_blocks.append({
                            "type": "BEARISH_BREAKER",
                            "level_high": float(current["high"]),
                            "level_low": float(current["low"]),
                            "description": "Failed bullish block - now bearish rejection zone",
                            "strength": 75
                        })
                        break
        
        # Look for bearish blocks that became bullish breakers
        for i in range(10, len(recent) - 5):
            current = recent.iloc[i]
            
            if current["close"] < current["open"]:  # Bearish candle
                # Check if price came back and broke it bullishly
                for j in range(i+1, min(i+10, len(recent))):
                    future = recent.iloc[j]
                    
                    if future["close"] > current["high"]:  # Broke the bearish block
                        breaker_blocks.append({
                            "type": "BULLISH_BREAKER",
                            "level_high": float(current["high"]),
                            "level_low": float(current["low"]),
                            "description": "Failed bearish block - now bullish support zone",
                            "strength": 75
                        })
                        break
        
        # Remove duplicates
        unique_blocks = []
        for block in breaker_blocks:
            if not any(abs(block["level_high"] - b["level_high"]) < 0.001 for b in unique_blocks):
                unique_blocks.append(block)
        
        return unique_blocks[:5]  # Return top 5
    
    def _detect_mitigation_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect mitigation blocks
        Zones where price returns to fill imbalances
        """
        
        mitigation_blocks = []
        recent = df.tail(40)
        
        # Look for gaps that got filled (mitigated)
        for i in range(1, len(recent) - 1):
            prev = recent.iloc[i-1]
            current = recent.iloc[i]
            next_candle = recent.iloc[i+1]
            
            # Bullish gap
            if current["low"] > prev["high"]:
                gap_start = prev["high"]
                gap_end = current["low"]
                
                # Check if gap was filled later
                for j in range(i+1, min(i+10, len(recent))):
                    future = recent.iloc[j]
                    if future["low"] <= gap_start:
                        mitigation_blocks.append({
                            "type": "BULLISH_MITIGATION",
                            "level_high": float(gap_end),
                            "level_low": float(gap_start),
                            "description": "Bullish gap filled - mitigation complete"
                        })
                        break
            
            # Bearish gap
            elif current["high"] < prev["low"]:
                gap_start = prev["low"]
                gap_end = current["high"]
                
                # Check if gap was filled later
                for j in range(i+1, min(i+10, len(recent))):
                    future = recent.iloc[j]
                    if future["high"] >= gap_start:
                        mitigation_blocks.append({
                            "type": "BEARISH_MITIGATION",
                            "level_high": float(gap_start),
                            "level_low": float(gap_end),
                            "description": "Bearish gap filled - mitigation complete"
                        })
                        break
        
        return mitigation_blocks[:5]
    
    def _detect_rejection_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect strong rejection zones
        Areas where price showed strong rejection (long wicks)
        """
        
        rejection_blocks = []
        recent = df.tail(30)
        
        for i, row in recent.iterrows():
            body_size = abs(row["close"] - row["open"])
            upper_wick = row["high"] - max(row["open"], row["close"])
            lower_wick = min(row["open"], row["close"]) - row["low"]
            
            # Strong upper wick rejection (bearish)
            if upper_wick > body_size * 2:
                rejection_blocks.append({
                    "type": "BEARISH_REJECTION",
                    "level": float(row["high"]),
                    "description": "Strong rejection from high",
                    "strength": 70
                })
            
            # Strong lower wick rejection (bullish)
            if lower_wick > body_size * 2:
                rejection_blocks.append({
                    "type": "BULLISH_REJECTION",
                    "level": float(row["low"]),
                    "description": "Strong rejection from low",
                    "strength": 70
                })
        
        return rejection_blocks[:5]
    
    def _empty_result(self) -> Dict:
        return {
            "breaker_blocks": [],
            "mitigation_blocks": [],
            "rejection_blocks": [],
            "confidence": 0
        }


# Singleton
breaker_blocks_detector = BreakerBlocksDetector()
