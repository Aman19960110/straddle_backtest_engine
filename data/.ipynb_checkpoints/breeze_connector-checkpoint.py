from breeze_connect import BreezeConnect
from datetime import datetime
import pandas as pd
from typing import Optional, Dict
import time
from app_config.app_config import StraddleConfig

class BreezeDataConnector:
    def __init__(self, api_key: str, api_secret: str, session_token: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_token = session_token

    def connect(self) -> bool:
        #authenticate with breeze api and return True if successful, False otherwise
        try:
            self.breeze = BreezeConnect(api_key=self.api_key, api_secret=self.api_secret, session_token=self.session_token)
            return True
        except Exception as e:
            print(f"Error connecting to Breeze API: {e}")
            return False