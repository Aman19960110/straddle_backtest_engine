# data/breeze_connector.py

from breeze_connect import BreezeConnect
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Dict

class BreezeDataConnector:
    """Wrapper for Breeze API to fetch options and spot data"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_token = None
        self.breeze = None
        
    def authenticate(self, session_token: str) -> bool:
        """
        Authenticate with Breeze API
        
        Parameters:
        -----------
        session_token: Session token from ICICI Direct
        
        Returns:
        --------
        bool: True if authentication successful
        """
        try:
            self.session_token = session_token
            self.breeze = BreezeConnect(api_key=self.api_key)
            self.breeze.generate_session(
                api_secret=self.api_secret,
                session_token=session_token
            )
            print("✅ Breeze API connected successfully.")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _normalize_api_response_to_df(self, data):
        """
        Normalize API response to DataFrame
        
        Parameters:
        -----------
        data: Raw API response
        
        Returns:
        --------
        DataFrame or None
        """
        if data is None:
            return None
        
        if isinstance(data, dict) and "Success" in data:
            payload = data["Success"]
        else:
            payload = data
        
        try:
            df = pd.DataFrame(payload)
            if df.empty:
                return None
            
            # Handle datetime column
            dt_candidates = [c for c in df.columns if c.lower() in ("datetime", "date", "time", "timestamp")]
            if dt_candidates:
                df["datetime"] = pd.to_datetime(df[dt_candidates[0]], errors="coerce")
            
            # Handle close price column
            if "close" not in df.columns:
                alt_close = next((c for c in df.columns if c.lower() in ("closeprice", "last", "ltp", "lastprice")), None)
                if alt_close:
                    df["close"] = pd.to_numeric(df[alt_close], errors="coerce")
            
            return df
        except Exception:
            return None
    
    def get_historical_options_data(self,
                                   interval: str,
                                   start_date: str,
                                   end_date: str,
                                   stock_code: str,
                                   expiry_date: str,
                                   right: str,
                                   strike_price: int) -> Optional[pd.DataFrame]:
        """
        Fetch historical options data from Breeze API
        
        Parameters:
        -----------
        interval: 1minute, 5minute, 30minute, 1day
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        stock_code: NIFTY, CNXBAN, FINNIFTY
        expiry_date: Expiry date (YYYY-MM-DD)
        right: call or put
        strike_price: Strike price as integer
        
        Returns:
        --------
        DataFrame with historical options data
        """
        try:
            data = self.breeze.get_historical_data_v2(
                interval=interval,
                from_date=f"{start_date}T09:15:00.000Z",
                to_date=f"{end_date}T15:30:00.000Z",
                stock_code=stock_code,
                exchange_code="NFO",
                product_type="options",
                expiry_date=f"{expiry_date}T15:30:00.000Z" if expiry_date else None,
                right=right,
                strike_price=str(strike_price),
            )
            
            df = self._normalize_api_response_to_df(data)
            
            if df is None or "datetime" not in df.columns:
                print("❌ Error fetching option data: invalid response")
                return None
            
            return df.sort_values("datetime").reset_index(drop=True)
        
        except Exception as e:
            print(f"❌ Error fetching historical options data: {e}")
            return None
    
    def get_historical_equity_data(self,
                                   interval: str,
                                   start_date: str,
                                   end_date: str,
                                   stock_code: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical equity/index data from Breeze API
        
        Parameters:
        -----------
        interval: 1minute, 5minute, 30minute, 1day
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        stock_code: NIFTY, CNXBAN, FINNIFTY
        
        Returns:
        --------
        DataFrame with historical equity data
        """
        try:
            data = self.breeze.get_historical_data_v2(
                interval=interval,
                from_date=f"{start_date}T09:15:00.000Z",
                to_date=f"{end_date}T15:30:00.000Z",
                stock_code=stock_code,
                exchange_code="NSE",
                product_type="cash",
            )
            
            df = self._normalize_api_response_to_df(data)
            
            if df is None or "datetime" not in df.columns:
                print("❌ Error fetching equity data: invalid response")
                return None
            
            return df.sort_values("datetime").reset_index(drop=True)
        
        except Exception as e:
            print(f"❌ Error fetching equity data: {e}")
            return None
    
    def calculate_atm_strike(self, underlying_price: float, index: str) -> int:
        """
        Calculate ATM strike price based on spot
        
        Parameters:
        -----------
        underlying_price: Current spot price
        index: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY
        
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
        
        steps = strike_intervals.get(index, 50)
        remainder = underlying_price % steps
        
        if remainder >= steps / 2:
            return int(underlying_price - remainder + steps)
        else:
            return int(underlying_price - remainder)
