# data/data_loader.py

from datetime import datetime, timedelta
import pandas as pd
from typing import Optional
from .breeze_connector import BreezeDataConnector

class DataLoader:
    """Handles loading market data via Breeze API"""
    
    def __init__(self, connector: BreezeDataConnector):
        self.connector = connector
    
    def get_underlying_price(self, 
                            symbol: str, 
                            start_date: str, 
                            entry_time_str: str = "09:20:00") -> Optional[float]:
        """
        Get underlying price at specific time on a given date
        
        Parameters:
        -----------
        symbol: Stock symbol (NIFTY, BANKNIFTY, etc.)
        start_date: Date in YYYY-MM-DD format
        entry_time_str: Time in HH:MM:SS format
        
        Returns:
        --------
        float: Underlying price or None if not found
        """
        try:
            end_date = str((pd.to_datetime(start_date) + timedelta(days=1)).date())
            
            data = self.connector.get_historical_equity_data(
                interval="1minute",
                start_date=start_date,
                end_date=end_date,
                stock_code=symbol
            )
            
            if data is None or data.empty:
                print(f"⚠️ No underlying data for {symbol} on {start_date}")
                return None
            
            data["datetime"] = pd.to_datetime(data["datetime"]).dt.tz_localize(None)
            target_ts = pd.to_datetime(f"{start_date} {entry_time_str}")
            
            row = data[data["datetime"] >= target_ts]
            
            if row.empty:
                print(f"⚠️ No {entry_time_str} price for {symbol} on {start_date}")
                return None
            
            return float(row.iloc[0]["close"])
        
        except Exception as e:
            print(f"❌ Failed to get underlying price: {e}")
            return None
    
    def get_options_data(self,
                        interval: str,
                        start_date: str,
                        stock_code: str,
                        expiry_date: str,
                        right: str,
                        strike_price: int) -> Optional[pd.DataFrame]:
        """
        Get options data for specific strike
        
        Parameters:
        -----------
        interval: 1minute, 5minute, etc.
        start_date: Date in YYYY-MM-DD format
        stock_code: NIFTY, CNXBAN, FINNIFTY
        expiry_date: Expiry date in YYYY-MM-DD format
        right: call or put
        strike_price: Strike price as integer
        
        Returns:
        --------
        DataFrame with options data
        """
        end_date = str((pd.to_datetime(start_date) + timedelta(days=1)).date())
        
        return self.connector.get_historical_options_data(
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            stock_code=stock_code,
            expiry_date=expiry_date,
            right=right,
            strike_price=strike_price
        )
