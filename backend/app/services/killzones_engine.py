"""
Mosh AI Pro v5 - Killzones Engine
Analyzes optimal trading times based on institutional activity
Asia, London, New York sessions
"""

import pandas as pd
from datetime import datetime, time as dt_time
from typing import Dict
from loguru import logger
import pytz


class KillzonesEngine:
    """
    Analyzes trading session strength and optimal entry times
    - Asia Session: 00:00-08:00 UTC
    - London Session: 08:00-16:00 UTC
    - New York Session: 13:00-22:00 UTC
    - London/NY Overlap: 13:00-16:00 UTC (most volatile)
    """
    
    def analyze(self, current_time: datetime = None) -> Dict:
        """Analyze current killzone and strength"""
        
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        try:
            current_hour = current_time.hour
            
            # Determine current session
            session = self._get_current_session(current_hour)
            
            # Get session strength
            strength = self._get_session_strength(session, current_hour)
            
            # Optimal entry recommendation
            optimal = self._is_optimal_time(session, current_hour)
            
            result = {
                "current_session": session,
                "session_strength": strength,
                "is_optimal_time": optimal,
                "recommendation": self._get_recommendation(session, optimal),
                "next_session": self._get_next_session(session),
                "confidence": 80.0 if optimal else 60.0
            }
            
            logger.info(f"🕐 Killzone: {session} (Strength: {strength}%) - Optimal: {optimal}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Killzones analysis: {e}")
            return self._empty_result()
    
    def _get_current_session(self, hour: int) -> str:
        """Determine current trading session"""
        
        if 0 <= hour < 8:
            return "ASIA"
        elif 8 <= hour < 13:
            return "LONDON"
        elif 13 <= hour < 16:
            return "LONDON_NY_OVERLAP"
        elif 16 <= hour < 22:
            return "NEWYORK"
        else:
            return "OFF_HOURS"
    
    def _get_session_strength(self, session: str, hour: int) -> float:
        """Calculate session strength (0-100)"""
        
        strengths = {
            "ASIA": 60,
            "LONDON": 85,
            "LONDON_NY_OVERLAP": 95,
            "NEWYORK": 85,
            "OFF_HOURS": 30
        }
        
        return strengths.get(session, 50)
    
    def _is_optimal_time(self, session: str, hour: int) -> bool:
        """Check if current time is optimal for trading"""
        
        # Best times:
        # - London open: 08:00-10:00
        # - NY open: 13:00-15:00
        # - Overlap: 13:00-16:00
        
        optimal_hours = [8, 9, 13, 14, 15]
        return hour in optimal_hours
    
    def _get_recommendation(self, session: str, optimal: bool) -> str:
        """Get trading recommendation"""
        
        if session == "LONDON_NY_OVERLAP":
            return "PRIME_TIME"
        elif optimal:
            return "GOOD_TIME"
        elif session in ["LONDON", "NEWYORK"]:
            return "ACCEPTABLE"
        else:
            return "WAIT_FOR_BETTER_TIME"
    
    def _get_next_session(self, current: str) -> str:
        """Get next trading session"""
        
        transitions = {
            "ASIA": "LONDON",
            "LONDON": "LONDON_NY_OVERLAP",
            "LONDON_NY_OVERLAP": "NEWYORK",
            "NEWYORK": "ASIA",
            "OFF_HOURS": "ASIA"
        }
        
        return transitions.get(current, "UNKNOWN")
    
    def _empty_result(self) -> Dict:
        return {
            "current_session": "UNKNOWN",
            "session_strength": 0,
            "is_optimal_time": False,
            "recommendation": "WAIT",
            "next_session": "UNKNOWN",
            "confidence": 0
        }


# Singleton
killzones_engine = KillzonesEngine()
