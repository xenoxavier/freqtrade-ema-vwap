"""
EmaVwapLong - High-expectancy Long strategy based on EMA9 x Daily-Anchored VWAP Crossover.

Origin & Forward-Test Provenance
---------------------------------
Ported directly from the forward-tested live shadow engine (vwapshadow.cjs)
running on the server's 30s price feed across 139 altcoins.

Forward-Test Metrics (6.2 days, 382 trades, Gate.io Futures):
  * Sizing: $10 margin @ 20x ($200 notional) -> +$783.40 Net USD (+78.34R)
  * Sizing: $1 margin @ 20x ($20 notional)   -> +$78.34 Net USD
  * Win Rate: 49.2% (188 Wins / 190 Losses / 3 Liquidations / 1 Expired)
  * Profit Factor: 2.02
  * Payoff Ratio: 2.12x (Average Win: +$0.83 vs Average Loss: -$0.39 on $1 margin)
  * Average Trade Duration: 9.87 hours
  * Distinct Coins Profitable: 65.5% (91 of 139 pairs)

The Core Edge: 1:2 Asymmetric Risk/Reward Ratio
------------------------------------------------
The strategy does not need a high win rate to be wildly profitable.
Because targets are 3.0x ATR and stops are 1.5x ATR (1:2 R:R), the strategy
only needs a 33.3% win rate to break even. At ~49% win rate, every winning trade
yields more than double the average loss.

Two-Stage Trigger Mechanism:
  1. ARMED:
     - 1h candle: EMA9 crosses above daily-anchored VWAP (reset at 00:00 UTC).
     - Rule 3: The crossover candle must close above BOTH EMA9 and VWAP.
     - Tradeability Filter: Stop distance (1.5 * ATR / trigger) must be < 3.8%.
       At 20x leverage, liquidation is ~4.0%. Refusing stops >= 3.8% guarantees
       the stop loss can fire without suffering an exchange liquidation.
     - Trigger price is recorded as the HIGH of the crossover candle.
  2. ENTERED:
     - The setup remains armed for up to 3 candles (ARM_BARS = 3).
     - Entry triggers when price breaks out above the Trigger High.
     - If EMA9 falls back below VWAP or 3 candles pass without a breakout,
       the setup expires and no capital is risked.

Exits:
  - Profit Target: Entry + 3.0 * ATR (+target_pct)
  - Stop Loss: Entry - 1.5 * ATR (-stop_pct), capped inside liquidation price
  - Time Stop: 60 hours maximum hold time
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy, stoploss_from_absolute

logger = logging.getLogger(__name__)

# Strategy Parameters
ARM_BARS = 3            # Max bars an armed setup can wait for a breakout
MAX_STOP_PCT = 3.8      # Maximum allowed stop distance (must be inside 20x liquidation)
MAX_HOLD_HOURS = 60.0   # Maximum hold time in hours
DEFAULT_LEVERAGE = 20.0 # Standard 20x isolated leverage
LIQ_SAFETY = 0.80       # Cap stoploss at 80% of distance to liquidation


class EmaVwapLong(IStrategy):
    INTERFACE_VERSION = 3

    # Long-only futures strategy
    can_short = False
    timeframe = "1h"

    # Exits are managed entirely by custom_exit and custom_stoploss
    minimal_roi = {"0": 10.0}  # Fallback high ROI
    stoploss = -0.99           # Wide safety net; custom_stoploss handles exact ATR stops
    use_custom_stoploss = True
    trailing_stop = False

    # Check entries and exits on every loop
    process_only_new_candles = False
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count = 50

    # Order types
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
    }

    # Protections to prevent overtrading and stop-out cascades
    @property
    def protections(self):
        return [
            # Cooldown: Do not re-enter the same coin for 2 candles after an exit
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            # Stoploss Guard: 2 stop-outs on a single coin within 24 hours locks it for 12 hours
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": True,
            },
            # Circuit Breaker: 5 stop-outs across ALL pairs within 6 hours pauses trading for 2 hours
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 6,
                "trade_limit": 5,
                "stop_duration_candles": 2,
                "only_per_pair": False,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators matching the vwapshadow.cjs specification:
          - EMA 9 on close
          - Daily-anchored VWAP (reset at 00:00 UTC)
          - ATR(14) with exponential smoothing
          - Crossover detection & arming propagation
        """
        if len(dataframe) < 40:
            return dataframe

        # 1. EMA 9
        dataframe["ema9"] = ta.EMA(dataframe["close"], timeperiod=9)

        # 2. Daily-Anchored VWAP (resets at 00:00 UTC each day)
        # Typical Price = (High + Low + Close) / 3
        typical_price = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3.0
        pv = typical_price * dataframe["volume"]

        # Ensure datetime index or UTC series for daily grouping
        date_series = pd.to_datetime(dataframe["date"])
        day_group = date_series.dt.floor("D")

        cum_pv = pv.groupby(day_group).cumsum()
        cum_vol = dataframe["volume"].groupby(day_group).cumsum()

        # Handle zero volume candles by falling back to close
        dataframe["vwap"] = np.where(cum_vol > 0, cum_pv / cum_vol, dataframe["close"])

        # 3. ATR(14) with Exponential Smoothing (matching Wilder/EMA specification)
        # TR = max(H - L, |H - C_prev|, |L - C_prev|)
        prev_close = dataframe["close"].shift(1)
        tr = np.maximum(
            dataframe["high"] - dataframe["low"],
            np.maximum(
                (dataframe["high"] - prev_close).abs(),
                (dataframe["low"] - prev_close).abs()
            )
        )
        # Smoothing with span 14 (alpha = 2 / (14 + 1) = 2/15)
        dataframe["atr"] = tr.ewm(span=14, adjust=False).mean()

        # 4. Cross Detection on closed candle
        # EMA9 crosses above VWAP
        ema_prev = dataframe["ema9"].shift(1)
        vwap_prev = dataframe["vwap"].shift(1)
        cross_above = (dataframe["ema9"] > dataframe["vwap"]) & (ema_prev <= vwap_prev)

        # Rule 3: Cross candle must close ABOVE both EMA9 and VWAP
        candle_above = (dataframe["close"] > dataframe["ema9"]) & (dataframe["close"] > dataframe["vwap"])
        valid_cross = cross_above & candle_above

        # 5. Calculate Setup Geometry at Cross
        trigger = np.where(valid_cross, dataframe["high"], np.nan)
        atr_at_cross = np.where(valid_cross, dataframe["atr"], np.nan)
        stop_pct = np.where(
            valid_cross & (trigger > 0),
            (1.5 * atr_at_cross / trigger) * 100.0,
            np.nan
        )
        target_pct = np.where(
            valid_cross & (trigger > 0),
            (3.0 * atr_at_cross / trigger) * 100.0,
            np.nan
        )
        # Tradeable filter: Stop must be within 3.8%
        tradeable = valid_cross & (stop_pct < MAX_STOP_PCT)

        dataframe["is_cross"] = valid_cross
        dataframe["cross_trigger"] = trigger
        dataframe["cross_stop_pct"] = stop_pct
        dataframe["cross_target_pct"] = target_pct
        dataframe["cross_tradeable"] = tradeable

        # 6. Propagate Armed State Forward across up to ARM_BARS (3 bars)
        # Setup remains armed if:
        #   - Cross occurred within ARM_BARS
        #   - EMA9 has remained above VWAP continuously since cross
        #   - Setup was tradeable (stop < 3.8%)
        armed = np.zeros(len(dataframe), dtype=bool)
        arm_trigger = np.full(len(dataframe), np.nan)
        arm_stop_pct = np.full(len(dataframe), np.nan)
        arm_target_pct = np.full(len(dataframe), np.nan)

        n = len(dataframe)
        ema_vals = dataframe["ema9"].values
        vwap_vals = dataframe["vwap"].values
        tradeable_vals = tradeable.values
        trigger_vals = trigger.values
        stop_vals = stop_pct.values
        target_vals = target_pct.values

        for i in range(n):
            # Check backwards up to ARM_BARS for a valid cross
            for bar_offset in range(0, ARM_BARS + 1):
                ci = i - bar_offset
                if ci < 0:
                    break
                if tradeable_vals[ci]:
                    # Check if EMA9 stayed above VWAP for all bars from ci to i
                    voided = False
                    for j in range(ci + 1, i + 1):
                        if ema_vals[j] <= vwap_vals[j]:
                            voided = True
                            break
                    if not voided:
                        armed[i] = True
                        arm_trigger[i] = trigger_vals[ci]
                        arm_stop_pct[i] = stop_vals[ci]
                        arm_target_pct[i] = target_vals[ci]
                        break

        dataframe["armed"] = armed
        dataframe["arm_trigger"] = arm_trigger
        dataframe["arm_stop_pct"] = arm_stop_pct
        dataframe["arm_target_pct"] = arm_target_pct

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Signals an entry when the setup is armed and price breaks out above the trigger high.
        """
        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = ""

        # Breakout condition:
        # Must be armed, and current price (high or close) >= trigger
        breakout = (
            dataframe["armed"] &
            (dataframe["high"] >= dataframe["arm_trigger"]) &
            (dataframe["arm_stop_pct"] < MAX_STOP_PCT)
        )

        dataframe.loc[breakout, "enter_long"] = 1

        # Embed stop_pct and target_pct into enter_tag for robust persistence
        for idx in dataframe[breakout].index:
            s_pct = dataframe.loc[idx, "arm_stop_pct"]
            t_pct = dataframe.loc[idx, "arm_target_pct"]
            dataframe.loc[idx, "enter_tag"] = f"vwap_s{s_pct:.2f}_t{t_pct:.2f}"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exits are handled dynamically in custom_exit and custom_stoploss.
        """
        dataframe["exit_long"] = 0
        return dataframe

    # ----------------------------------------------------------- Custom Stop Loss
    def custom_stoploss(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs
    ) -> float:
        """
        Calculates the stop loss price based on 1.5 * ATR distance recorded at entry.
        Also guarantees the stop stays inside the exchange liquidation price.
        """
        # Parse stop_pct from enter_tag (e.g., 'vwap_s1.85_t3.70')
        stop_pct = self._parse_tag(trade.enter_tag, "s", fallback=2.0)
        entry_rate = trade.open_rate or current_rate

        # Desired stop price: entry * (1 - stop_pct / 100)
        stop_price = entry_rate * (1.0 - (stop_pct / 100.0))

        # Check liquidation price if available from exchange
        liq = getattr(trade, "liquidation_price", None)
        if liq and liq < entry_rate:
            # Long: liquidation is below entry. Cap stoploss inside liquidation
            safe_liq_stop = entry_rate - (entry_rate - liq) * LIQ_SAFETY
            stop_price = max(stop_price, safe_liq_stop)

        # Convert absolute stop price to leveraged ratio
        ratio = stoploss_from_absolute(
            stop_price,
            current_rate,
            is_short=trade.is_short,
            leverage=trade.leverage or DEFAULT_LEVERAGE
        )
        return ratio if ratio is not None else -0.99

    # ----------------------------------------------------------- Custom Exit (Target & Timeout)
    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        Checks for:
          1. Profit Target hit (+3.0 * ATR distance = 1:2 R:R)
          2. Timeout expiration after 60 hours
        """
        entry_rate = trade.open_rate or current_rate
        target_pct = self._parse_tag(trade.enter_tag, "t", fallback=4.0)

        # Target Price: entry * (1 + target_pct / 100)
        target_price = entry_rate * (1.0 + (target_pct / 100.0))

        # 1. Take Profit
        if current_rate >= target_price:
            return "target_hit_1_to_2_rr"

        # 2. Time Expiration (60 hours)
        trade_open_date = trade.open_date_utc
        if trade_open_date:
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
            if trade_open_date.tzinfo is None:
                trade_open_date = trade_open_date.replace(tzinfo=timezone.utc)

            if current_time - trade_open_date >= timedelta(hours=MAX_HOLD_HOURS):
                return "time_expired_60h"

        return None

    # ----------------------------------------------------------- Dynamic Leverage
    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Sets leverage to 20x (or exchange max if lower).
        """
        return min(DEFAULT_LEVERAGE, max_leverage)

    # ----------------------------------------------------------- Helper Parsing
    @staticmethod
    def _parse_tag(tag: Optional[str], key: str, fallback: float) -> float:
        """
        Extracts parameter values from enter_tag.
        Example: 'vwap_s1.85_t3.70' -> key='s' yields 1.85, key='t' yields 3.70.
        """
        if not tag:
            return fallback
        parts = tag.split("_")
        for part in parts:
            if part.startswith(key):
                try:
                    return float(part[len(key):])
                except ValueError:
                    pass
        return fallback
