# strategy/straddle_strategy.py

import pandas as pd
from datetime import timedelta
from typing import Tuple

class StraddleStrategy:
    """
    Short Straddle Strategy Implementation with SL/TP
    """
    
    def __init__(self, config):
        self.entry_time = config.entry_time
        self.exit_time = config.exit_time
        self.lot_size = config.lot_size
        self.stop_loss_pct = config.stop_loss_pct
        self.take_profit_pct = config.target_profit_pct
        self.per_leg = config.per_leg
        self.index = config.index
    
    def calculate_atm_strike(self, underlying_price: float) -> int:
        """
        Calculate ATM strike price based on spot
        
        Parameters:
        -----------
        underlying_price: Current spot price
        
        Returns:
        --------
        int: ATM strike price
        """
        strike_intervals = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'FINNIFTY': 50,
            'MIDCPNIFTY': 25
        }
        
        steps = strike_intervals.get(self.index, 50)
        remainder = underlying_price % steps
        
        if remainder >= steps / 2:
            return int(underlying_price - remainder + steps)
        else:
            return int(underlying_price - remainder)
    
    def run(self, 
            underlying_price: float,
            call_df: pd.DataFrame,
            put_df: pd.DataFrame) -> Tuple:
        """
        Execute straddle strategy
        
        Parameters:
        -----------
        underlying_price: Current underlying price
        call_df: Call option data
        put_df: Put option data
        
        Returns:
        --------
        Tuple of (pnl, ce_entry, pe_entry, ce_exit, pe_exit, pnl_df, 
                 exited_flag, exit_time_actual, exit_reason)
        """
        if call_df is None or put_df is None or call_df.empty or put_df.empty:
            raise ValueError("Call or Put data missing/empty for strategy.run")
        
        entry_date = pd.to_datetime(call_df.iloc[0]["datetime"]).date().strftime("%Y-%m-%d")
        entry_time = pd.to_datetime(f"{entry_date} {self.entry_time}")
        exit_time = pd.to_datetime(f"{entry_date} {self.exit_time}")
        
        ce_candidates = call_df[pd.to_datetime(call_df["datetime"]) >= entry_time]
        pe_candidates = put_df[pd.to_datetime(put_df["datetime"]) >= entry_time]
        
        if ce_candidates.empty or pe_candidates.empty:
            raise ValueError("No CE/PE bars at or after entry time")
        
        ce_entry = float(ce_candidates.iloc[0]["close"])
        pe_entry = float(pe_candidates.iloc[0]["close"])
        
        pnl_df, exited_flag, exit_time_actual, exit_reason = self.get_minute_pnl(
            call_df, put_df, ce_entry, pe_entry, entry_time, exit_time
        )
        
        # Final exit prices (last row in pnl_df)
        ce_exit = float(pnl_df.iloc[-1]["close_ce"])
        pe_exit = float(pnl_df.iloc[-1]["close_pe"])
        
        # P&L for short straddle
        pnl = (ce_entry + pe_entry) - (ce_exit + pe_exit)
        
        return pnl, ce_entry, pe_entry, ce_exit, pe_exit, pnl_df, exited_flag, exit_time_actual, exit_reason
    
    def get_minute_pnl(self,
                      call_df: pd.DataFrame,
                      put_df: pd.DataFrame,
                      ce_entry: float,
                      pe_entry: float,
                      entry_time: pd.Timestamp,
                      exit_time: pd.Timestamp) -> Tuple:
        """
        Calculate minute-by-minute P&L and check for SL/TP exits
        
        Returns:
        --------
        Tuple of (pnl_df, exited_flag, exit_time_actual, exit_reason)
        """
        call_df = call_df.copy()
        put_df = put_df.copy()
        call_df["datetime"] = pd.to_datetime(call_df["datetime"])
        put_df["datetime"] = pd.to_datetime(put_df["datetime"])
        
        ce_filtered = call_df[(call_df["datetime"] >= entry_time) & (call_df["datetime"] <= exit_time)]
        pe_filtered = put_df[(put_df["datetime"] >= entry_time) & (put_df["datetime"] <= exit_time)]
        
        df = pd.merge(
            ce_filtered[["datetime", "close"]],
            pe_filtered[["datetime", "close"]],
            on="datetime",
            suffixes=("_ce", "_pe")
        )
        
        if df.empty:
            raise ValueError("No overlapping minute bars between CE and PE in window")
        
        # Calculate P&L (positive = profit for short straddle)
        df["MinutePnL"] = (ce_entry + pe_entry) - (df["close_ce"] + df["close_pe"])
        df["CumulativePnL"] = df["MinutePnL"] * self.lot_size
        
        sl_triggered = False
        tp_triggered = False
        exit_reason = "Exit"
        exit_time_actual = df["datetime"].iloc[-1]
        
        total_entry = ce_entry + pe_entry
        
        # Iterate through each minute to check for SL/TP
        for i, row in df.iterrows():
            ce_price = row["close_ce"]
            pe_price = row["close_pe"]
            
            if not self.per_leg:
                # Combined SL/TP mode
                total_premium = ce_price + pe_price
                loss_pct = ((total_premium - total_entry) / total_entry) * 100
                profit_pct = ((total_entry - total_premium) / total_entry) * 100
                
                # Stop Loss check
                if loss_pct >= self.stop_loss_pct:
                    sl_triggered = True
                    exit_reason = "StopLoss"
                    exit_time_actual = row["datetime"]
                    df = df.iloc[:i + 1]
                    break
                
                # Take Profit check
                if self.take_profit_pct is not None and profit_pct >= self.take_profit_pct:
                    tp_triggered = True
                    exit_reason = "TakeProfit"
                    exit_time_actual = row["datetime"]
                    df = df.iloc[:i + 1]
                    break
            
            else:
                # Per-leg SL/TP mode
                ce_loss_pct = ((ce_price - ce_entry) / ce_entry) * 100
                pe_loss_pct = ((pe_price - pe_entry) / pe_entry) * 100
                
                # Stop Loss - either leg
                if ce_loss_pct >= self.stop_loss_pct or pe_loss_pct >= self.stop_loss_pct:
                    sl_triggered = True
                    exit_reason = "StopLoss"
                    exit_time_actual = row["datetime"]
                    df = df.iloc[:i + 1]
                    break
                
                # Take Profit - either leg
                if self.take_profit_pct is not None:
                    ce_profit_pct = ((ce_entry - ce_price) / ce_entry) * 100
                    pe_profit_pct = ((pe_entry - pe_price) / pe_entry) * 100
                    
                    if ce_profit_pct >= self.take_profit_pct or pe_profit_pct >= self.take_profit_pct:
                        tp_triggered = True
                        exit_reason = "TakeProfit"
                        exit_time_actual = row["datetime"]
                        df = df.iloc[:i + 1]
                        break
        
        exited_flag = sl_triggered or tp_triggered or (exit_reason == "Exit")
        
        return df.reset_index(drop=True), exited_flag, exit_time_actual, exit_reason
