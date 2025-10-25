# config/config.py

from dataclasses import dataclass
from typing import Optional
import yaml
import os

@dataclass
class StraddleConfig:
    # Breeze API Credentials
    api_key: str
    api_secret: str
    session_token: str

    # Strategy Settings
    index: str = "NIFTY"
    entry_time: str = "09:20:00"
    exit_time: str = "15:20:00"

    # Straddle Settings
    strike_selection: str = "ATM"
    lot_size: int = 75

    # Risk Management
    stop_loss_pct: float = 25.0
    target_profit_pct: Optional[float] = None
    max_loss_per_day: float = 10000
    per_leg: bool = True

    # Re-entry Settings
    max_reentries: int = 10
    reentry_delay_minutes: int = 5





    # Trading Costs
    commission_per_lot: float = 20
    slippage_points: float = 0.3

    @classmethod
    def from_yaml(cls, filepath: str = None):
        """
        Loads config from a YAML file. Default path is ./config/credentials.yml.
        """
        if filepath is None:
            filepath = os.path.join(os.path.dirname(__file__), 'credentials.yml')
        
        with open(filepath, 'r') as file:
            config_dict = yaml.safe_load(file)
        
        # Convert null YAML to None in Python for Optional types
        if 'target_profit_pct' in config_dict and config_dict['target_profit_pct'] is None:
            config_dict['target_profit_pct'] = None
        
        return cls(**config_dict)
