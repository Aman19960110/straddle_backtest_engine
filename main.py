# main.py

from app_config import StraddleConfig
from data.breeze_connector import BreezeDataConnector
from data.data_loader import DataLoader
from strategy.straddle_strategy import StraddleStrategy
from utils.report_generator import generate_report
from engine.engine import BacktestEngine
import time
from tqdm import tqdm

import pandas as pd
from datetime import timedelta, datetime
from typing import List
import os
import numpy as np


if __name__ == "__main__":

    start_time = time.time()
    print(f"\n🟢 Backtest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # Load configuration
    config = StraddleConfig.from_yaml()
    
    # Initialize backtest engine
    engine = BacktestEngine(config)
    
    # Define backtest schedule
    symbol = "NIFTY"
    backtest_schedule = [
        ('2024-12-27', '2025-01-02'),
        ('2024-12-30', '2025-01-02'),
        ('2024-12-31', '2025-01-02'),
        ('2025-01-01', '2025-01-02'),
        ('2025-01-02', '2025-01-02'),
        ('2025-01-03', '2025-01-09'),
        ('2025-01-06', '2025-01-09'),
        ('2025-01-07', '2025-01-09'),
        ('2025-01-08', '2025-01-09'),
        ('2025-01-09', '2025-01-09'),
    ]

    # Run all backtests (no exports inside loop)
    for date, expiry in backtest_schedule:
        print(f"\n🚀 Running backtest for {date} | Expiry {expiry}")
        engine.run_backtest(symbol=symbol, expiry=expiry, dates=[date])
        

    # ✅ Single combined export
    if engine.results:
        combined_df = pd.DataFrame(engine.results)
        print(f"\n📈 Total Trades: {len(combined_df)} across {len(backtest_schedule)} sessions")

        # Export consolidated results
        engine.export_results_to_csv(combined_df)
        engine.summary(export_csv=True)
        engine.export_all_intraday_pnl()

        print("\n✅  consolidated report generated in 'backtest_results/' folder")
    else:
        print("⚠️ No trades found — check data or strategy settings.")

    # --- ✅ Timing summary ---
    end_time = time.time()
    total_seconds = end_time - start_time
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)

    print(f"\n🕒 Backtest finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱ Total backtest duration: {minutes} min {seconds} sec ({total_seconds/60:.2f} minutes total)")

