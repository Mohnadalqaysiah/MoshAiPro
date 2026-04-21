"""
أداة لاستبدال دوال الـ validation القديمة بـ _institutional_gate الجديد
"""
import os

TARGET = os.path.join(os.path.dirname(__file__), '..', 'app', 'services', 'ai_engine_v5.py')

with open(TARGET, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 647-1121 (1-indexed) = index 646-1120 (0-indexed)
# We keep [0..645] + new_block + [1121..end]
before = lines[:646]
after  = lines[1121:]

new_block = '''\
    # ═══════════════════════════════════════════════════════════════════════
    # INSTITUTIONAL GATE — Single authoritative validation (Rules 1-16)
    # ═══════════════════════════════════════════════════════════════════════

    # Rule 5 — entry tolerance per timeframe
    _ENTRY_TOLERANCE = {
        "1m": 0.001, "5m": 0.001, "15m": 0.001,
        "30m": 0.002, "1h": 0.002, "4h": 0.003, "1d": 0.003,
    }

    # Rule 11 — cooldown per timeframe (seconds)
    _COOLDOWN_SEC = {
        "1m": 300, "5m": 900, "15m": 2700,
        "30m": 3600, "1h": 7200, "4h": 14400, "1d": 43200,
    }

    # Rule 9 — default spread per symbol
    _DEFAULT_SPREAD = {
        "XAUUSD": 0.30, "XAGUSD": 0.02, "BTCUSD": 8.0, "ETHUSD": 0.8,
        "EURUSD": 0.0001, "GBPUSD": 0.0002, "USDJPY": 0.02, "USDCHF": 0.0002,
        "NAS100": 1.0, "US30": 2.0, "USOIL": 0.04, "BRENT": 0.04,
    }

    def _institutional_gate(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        INSTITUTIONAL MODE Hard Rejection Gate (Rules 1-16).
        ICT Engine is the SOLE source of direction and trade levels.
        Any single check failure -> REJECT immediately, no exceptions.
        """
        rec = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return analysis

        levels  = analysis.get("levels", {})
        entry   = float(levels.get("entry") or 0)
        sl      = float(levels.get("stop_loss") or 0)
        tp1_raw = float(levels.get("tp1") or 0)
        tp2_raw = float(levels.get("tp2") or 0)

        if not entry or not sl or not tp1_raw:
            return self._hard_reject(analysis, "MISSING_LEVELS")

        # Rule 2: Direction must match ICT confluence
        ict_dir = analysis.get("confluence", {}).get("direction", "WAIT")
        if ict_dir != rec:
            return self._hard_reject(analysis, "DIRECTION_MISMATCH_ICT")

        # Rule 3: Structure validation — sweep + aligned BOS/CHOCH
        struct   = analysis.get("market_structure", {})
        sweep    = analysis.get("liquidity_sweep", {})
        bos_list = struct.get("bos_events", [])

        has_sweep = (
            sweep.get("has_bullish_sweep") if rec == "BUY"
            else sweep.get("has_bearish_sweep")
        )
        has_aligned_bos = (
            any("BULLISH" in b.get("type", "") for b in bos_list) if rec == "BUY"
            else any("BEARISH" in b.get("type", "") for b in bos_list)
        )
        has_choch = bool(struct.get("choch_events"))

        if not has_sweep:
            return self._hard_reject(analysis, "NO_LIQUIDITY_SWEEP")
        if not has_aligned_bos and not has_choch:
            return self._hard_reject(analysis, "NO_BOS_NO_CHOCH")

        # Rule 4: Closest zone only, no overlap
        ob           = analysis.get("order_blocks", {})
        current_p    = float(analysis.get("current_price") or entry)
        support_zone = self._closest_zone(current_p, ob.get("bullish_obs", []))
        resist_zone  = self._closest_zone(current_p, ob.get("bearish_obs", []))

        if support_zone and resist_zone:
            if float(support_zone["high"]) > float(resist_zone["low"]):
                return self._hard_reject(analysis, "ZONE_OVERLAP")

        # Rule 5: Entry vs zone (dynamic tolerance)
        tol = self._ENTRY_TOLERANCE.get(timeframe, 0.002)
        if rec == "BUY" and support_zone:
            z_lo, z_hi = float(support_zone["low"]), float(support_zone["high"])
            if not (z_lo <= entry <= z_hi or abs(entry - z_hi) / entry <= tol):
                return self._hard_reject(analysis, "BUY_ENTRY_NOT_NEAR_SUPPORT")
        elif rec == "SELL" and resist_zone:
            z_lo, z_hi = float(resist_zone["low"]), float(resist_zone["high"])
            if not (z_lo <= entry <= z_hi or abs(entry - z_lo) / entry <= tol):
                return self._hard_reject(analysis, "SELL_ENTRY_NOT_NEAR_RESISTANCE")

        # Rule 6: TP/SL ordering + auto-fix swap
        tp1, tp2 = tp1_raw, tp2_raw
        if rec == "BUY":
            if sl >= entry:
                return self._hard_reject(analysis, "BUY_SL_ABOVE_ENTRY")
            if tp1 <= entry:
                return self._hard_reject(analysis, "BUY_TP1_BELOW_ENTRY")
            if tp2 and tp1 > tp2:
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1
        else:
            if sl <= entry:
                return self._hard_reject(analysis, "SELL_SL_BELOW_ENTRY")
            if tp1 >= entry:
                return self._hard_reject(analysis, "SELL_TP1_ABOVE_ENTRY")
            if tp2 and tp1 < tp2:
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1

        # Rule 7: Dynamic RR threshold
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp1 - entry)
        if sl_dist <= 0:
            return self._hard_reject(analysis, "ZERO_SL_DISTANCE")
        rr = round(tp_dist / sl_dist, 2)
        levels["risk_reward"] = rr
        analysis["risk_reward_ratio"] = rr
        min_rr = self._get_min_rr()
        if rr < min_rr:
            return self._hard_reject(analysis, f"RR_{rr:.2f}_BELOW_MIN_{min_rr:.1f}")

        # Rule 8: Distance filter
        if tp_dist / entry < 0.003:
            return self._hard_reject(analysis, "TP_TOO_CLOSE")
        if sl_dist / entry < 0.002:
            return self._hard_reject(analysis, "SL_TOO_CLOSE")

        # Rule 9: Spread filter (ATR*0.05 or default)
        atr    = float(levels.get("atr") or 0)
        spread = atr * 0.05 if atr > 0 else self._DEFAULT_SPREAD.get(symbol.upper(), entry * 0.0002)
        if spread / sl_dist > 0.30:
            return self._hard_reject(analysis, "SPREAD_EATS_RISK")

        # Rule 10: Liquidity-based TP override
        liquidity   = analysis.get("liquidity", {})
        nearest_bsl = liquidity.get("nearest_bsl")
        nearest_ssl = liquidity.get("nearest_ssl")

        if rec == "BUY" and nearest_bsl and float(nearest_bsl) > entry:
            liq_tp1 = float(nearest_bsl)
            liq_tp2 = round(liq_tp1 + (atr * 2 if atr else liq_tp1 * 0.005), 5)
            if abs(liq_tp1 - entry) / entry > 0.003:
                levels["tp1"] = round(liq_tp1, 5)
                levels["tp2"] = liq_tp2
                tp1 = liq_tp1
        elif rec == "SELL" and nearest_ssl and float(nearest_ssl) < entry:
            liq_tp1 = float(nearest_ssl)
            liq_tp2 = round(liq_tp1 - (atr * 2 if atr else liq_tp1 * 0.005), 5)
            if abs(entry - liq_tp1) / entry > 0.003:
                levels["tp1"] = round(liq_tp1, 5)
                levels["tp2"] = liq_tp2
                tp1 = liq_tp1

        # Rule 11: Cooldown
        if not self.check_cooldown(symbol, timeframe):
            return self._hard_reject(analysis, "COOLDOWN_ACTIVE")

        # Rule 14: Confidence system
        conf = float(analysis.get("ai_confidence_score") or 0)

        # HTF alignment
        if htf_analysis:
            htf_trend = htf_analysis.get("market_structure", {}).get("trend", "RANGING")
            if (rec == "BUY" and htf_trend == "BULLISH") or \
               (rec == "SELL" and htf_trend == "BEARISH"):
                conf = min(conf + 8, 95)
            elif (rec == "BUY" and htf_trend == "BEARISH") or \
                 (rec == "SELL" and htf_trend == "BULLISH"):
                conf = max(conf - 15, 0)
                if conf < 50:
                    return self._hard_reject(analysis, "HTF_CONFLICT")

        # Confidence cap by R/R (Rule 14)
        rr_final = round(abs(levels.get("tp1", tp1) - entry) / sl_dist, 2)
        conf = min(conf, 75.0) if rr_final < 2.0 else min(conf, 90.0)

        if conf < 55:
            return self._hard_reject(analysis, f"CONF_TOO_LOW_{conf:.0f}")

        analysis["ai_confidence_score"]    = conf
        analysis["institutional_gate_passed"] = True
        analysis["gate_rr"]               = rr_final
        logger.info(
            f"GATE PASSED [{rec}] {symbol}/{timeframe}: "
            f"entry={entry} rr={rr_final} conf={conf:.0f}%"
        )
        return analysis

    @staticmethod
    def _closest_zone(price: float, obs: list) -> Optional[dict]:
        valid = [o for o in obs if isinstance(o, dict) and o.get("low") and o.get("high")]
        if not valid:
            return None
        return min(valid, key=lambda o: abs((float(o["low"]) + float(o["high"])) / 2 - price))

    def _hard_reject(self, analysis: dict, reason: str) -> dict:
        rec = analysis.get("recommendation", "?")
        logger.warning(f"REJECTED [{rec}] {reason}")
        analysis.update({
            "recommendation":         "WAIT",
            "signal_type":            "WAIT",
            "ai_confidence_score":    min(float(analysis.get("ai_confidence_score") or 0), 45.0),
            "institutional_rejected": True,
            "rejection_reason":       reason,
            "levels":                 {},
            "entry_zones":            [],
            "stop_loss_zone":         None,
            "take_profit_zones":      [],
        })
        return analysis

    def _get_min_rr(self) -> float:
        wr = self.get_winrate()
        if wr > 0.60:  return 1.3
        if wr >= 0.40: return 1.5
        if wr >= 0.30: return 1.7
        return 2.0

    def check_cooldown(self, symbol: str, timeframe: str) -> bool:
        import time as _t
        key = f"{symbol.upper()}_{timeframe}"
        cooldown = self._COOLDOWN_SEC.get(timeframe, 3600)
        last = self._last_signal_time.get(key, 0)
        if _t.time() - last < cooldown:
            remaining = int(cooldown - (_t.time() - last))
            logger.info(f"Cooldown [{symbol}/{timeframe}]: {remaining}s left")
            return False
        return True

    def record_signal_sent(self, symbol: str, timeframe: str):
        import time as _t
        self._last_signal_time[f"{symbol.upper()}_{timeframe}"] = _t.time()

    def update_performance(self, result: str):
        if result == "WIN":    self._perf["wins"]   += 1
        elif result == "LOSS": self._perf["losses"] += 1

    def get_winrate(self) -> float:
        total = self._perf["wins"] + self._perf["losses"]
        return self._perf["wins"] / total if total > 0 else 0.55

    def load_performance_from_db(self, db_session) -> None:
        try:
            from app.models.signal import Signal, SignalStatus
            wins   = db_session.query(Signal).filter(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT])
            ).count()
            losses = db_session.query(Signal).filter(
                Signal.status == SignalStatus.SL_HIT
            ).count()
            self._perf = {"wins": wins, "losses": losses}
            logger.info(
                f"Performance loaded: {wins}W/{losses}L "
                f"winrate={self.get_winrate():.0%} "
                f"min_rr={self._get_min_rr()}"
            )
        except Exception as e:
            logger.warning(f"Could not load performance from DB: {e}")

'''

result = before + [new_block] + after

with open(TARGET, 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f"Done. Total lines: {len(result)}")
