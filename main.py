# main.py

from app_config import StraddleConfig
from data.breeze_connector import BreezeDataConnector
from data.data_loader import DataLoader
from strategy.straddle_strategy import StraddleStrategy
from utils.report_generator import generate_report

import pandas as pd
from datetime import timedelta, datetime
from typing import List
import os
import numpy as np

class BacktestEngine:
    """Main backtesting engine for straddle strategy"""
    
    def __init__(self, config: StraddleConfig):
        self.config = config
        
        # Initialize components
        self.connector = BreezeDataConnector(config.api_key, config.api_secret)
        self.connector.authenticate(config.session_token)
        
        self.data_loader = DataLoader(self.connector)
        self.strategy = StraddleStrategy(config)
        
        self.results = []
        self.minute_pnl_records = {}
        
        # Create output directory for CSV files
        self.output_dir = "backtest_results"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def run_backtest(self, symbol: str, expiry: str, dates: List[str]):
        """
        Run backtest for multiple dates
        
        Parameters:
        -----------
        symbol: Stock symbol (NIFTY, CNXBAN, etc.)
        expiry: Expiry date (YYYY-MM-DD)
        dates: List of trading dates (YYYY-MM-DD)
        """
        for date in dates:
            print(f"\n📅 Backtesting {symbol} on {date}")
            daily_pnl = 0
            try:
                underlying_price = self.data_loader.get_underlying_price(
                    symbol, date, self.config.entry_time
                )
                
                if underlying_price is None:
                    continue
                
                current_time = pd.to_datetime(f"{date} {self.config.entry_time}")
                current_underlying = underlying_price
                reentry = 0
                
                # Re-entry loop
                while reentry <= self.config.max_reentries:

                    if daily_pnl <= -self.config.max_loss_per_day:
                        print(f"🛑 Max daily loss reached ({daily_pnl:.2f}). Stopping trading for {date}.")
                        break    

                    atm_strike = self.strategy.calculate_atm_strike(current_underlying)
                    print(f"➡️ Re-entry #{reentry} | Strike {atm_strike}")
                    
                    # Fetch CE and PE data
                    ce_df = self.data_loader.get_options_data(
                        "1minute", date, symbol, expiry, "call", atm_strike
                    )
                    pe_df = self.data_loader.get_options_data(
                        "1minute", date, symbol, expiry, "put", atm_strike
                    )
                    
                    if ce_df is None or ce_df.empty or pe_df is None or pe_df.empty:
                        print("⚠️ Missing CE/PE data, skipping.")
                        break
                    
                    # Filter data from current_time
                    ce_df = ce_df[pd.to_datetime(ce_df["datetime"]) >= current_time]
                    pe_df = pe_df[pd.to_datetime(pe_df["datetime"]) >= current_time]
                    
                    if ce_df.empty or pe_df.empty:
                        print("⚠️ No valid minute data post entry.")
                        break
                    
                    # Run strategy
                    net_pnl,gross_pnl, ce_entry, pe_entry, ce_exit, pe_exit, pnl_df, exited_flag, exit_time, exit_reason = \
                        self.strategy.run(current_underlying, ce_df, pe_df)
                    
                    # Record trade
                    trade = {
                        "date": date,
                        "reentry": reentry,
                        "underlying_price": current_underlying,
                        "ATM Strike": atm_strike,
                        "CE Entry": ce_entry,
                        "PE Entry": pe_entry,
                        "CE Exit": ce_exit,
                        "PE Exit": pe_exit,
                        "gross_pnl": gross_pnl,
                        "net_PnL": net_pnl,
                        "ExitReason": exit_reason,
                        "EntryTime": current_time,
                        "ExitTime": exit_time,
                        "expiry" : expiry,
                    }
                    self.results.append(trade)
                    self.minute_pnl_records[f"{date}_reentry_{reentry}"] = pnl_df
                    
                    daily_pnl += net_pnl
                    print(f"💰 Cumulative PnL for {date}: {daily_pnl:.2f}")

                    # Check if should continue re-entry
                    if exit_reason == "TakeProfit" or exit_reason == "Exit":
                        break
                    
                    # Re-entry logic after SL
                    if exit_reason == "StopLoss" and reentry < self.config.max_reentries and exit_time is not None:
                        underlying_df = self.connector.get_historical_equity_data(
                            "1minute", date, date, symbol
                        )
                        
                        if underlying_df is None or underlying_df.empty:
                            print("⚠️ Could not fetch underlying after SL.")
                            break
                        
                        underlying_df["datetime"] = pd.to_datetime(underlying_df["datetime"])
                        row = underlying_df[underlying_df["datetime"] >= exit_time]
                        
                        if row.empty:
                            print("⚠️ No underlying after SL time.")
                            break
                        
                        current_underlying = float(row.iloc[0]["close"])
                        current_time = exit_time + timedelta(minutes=self.config.reentry_delay_minutes)
                        print(f"🔁 Re-entry after {self.config.reentry_delay_minutes} min | New entry time: {current_time}")
                        reentry += 1
                    else:
                        break
            
            except Exception as e:
                print(f"❌ Error on {date}: {e}")
        
        # Create results DataFrame
        results_df = pd.DataFrame(self.results)
        


    
    def export_results_to_csv(self, df: pd.DataFrame):
        """
        Export detailed results to CSV
        
        Parameters:
        -----------
        df: Results DataFrame
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/backtest_results_{timestamp}.csv"
        
        # Format datetime columns
        export_df = df.copy()
        export_df["EntryTime"] = pd.to_datetime(export_df["EntryTime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        export_df["ExitTime"] = pd.to_datetime(export_df["ExitTime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        export_df['date'] = pd.to_datetime(export_df['date'], errors='coerce')
        export_df['weekday'] = export_df['date'].dt.day_name()


        conditions_1 = [
        (export_df['weekday'] == 'Tuesday') & (export_df['date'] <= '2025-09-01'),
        (export_df['weekday'] == 'Wednesday')&(export_df['date'] <= '2025-09-01'),
        (export_df['weekday'] == 'Thursday')&(export_df['date'] <= '2025-09-01'),
        (export_df['weekday'] == 'Friday')&(export_df['date'] <= '2025-09-01'),
        (export_df['weekday'] == 'Monday')&(export_df['date'] <= '2025-09-01')
        ]
        choices_1 = [2,1,0,4,3]

        export_df['trading_dy_typ'] = np.select(conditions_1, choices_1, default=np.nan)        


        conditions = [
        (export_df['weekday'] == 'Tuesday') & (export_df['date'] >= '2025-09-01'),
        (export_df['weekday'] == 'Wednesday')&(export_df['date'] >= '2025-09-01'),
        (export_df['weekday'] == 'Thursday')&(export_df['date'] >= '2025-09-01'),
        (export_df['weekday'] == 'Friday')&(export_df['date'] >= '2025-09-01'),
        (export_df['weekday'] == 'Monday')&(export_df['date'] >= '2025-09-01')
        ]
        choices = [0,4,3,2,1]

        export_df['trading_dy_typ'] = np.select(conditions, choices, default=np.nan)
        # Add cumulative P&L
        export_df["CumulativePnL"] = export_df.groupby("date")["net_PnL"].cumsum()
        
        # Export to CSV
        export_df.to_csv(filename, index=False)
        print(f"\n✅ Results exported to: {filename}")
        
        try:
            print("\n📊 Generating QuantStats performance report...")
            generate_report(
                backtest_csv_path=filename,
                start_date="2025-01-01",
                end_date=datetime.now().strftime("%Y-%m-%d"),
                initial_capital=400000,
                rf_rate=0.065  # use 6.5% as Indian risk-free rate
            )
            print("✅ QuantStats report successfully created!\n")
        except Exception as e:
            print(f"⚠️ Failed to generate QuantStats report: {e}")  

        return filename
    
    def summary(self, export_csv: bool = True):
        """
        Generate backtest summary and statistics
        
        Parameters:
        -----------
        export_csv: If True, export summary to CSV
        
        Returns:
        --------
        Tuple of (results_df, daily_df, metrics_dict)
        """
        df = pd.DataFrame(self.results)
        
        if df.empty:
            print("❌ No results found.")
            return df, pd.DataFrame(), {}
        
        df["CumulativePnL"] = df.groupby("date")["net_PnL"].cumsum()
        df["EntryTime"] = pd.to_datetime(df["EntryTime"]).dt.strftime("%H:%M:%S")
        df["ExitTime"] = pd.to_datetime(df["ExitTime"]).dt.strftime("%H:%M:%S")
        
        print("\n📊 Backtest Summary:")
        print(df[["date", "reentry", "EntryTime", "ExitTime", "ExitReason", "net_PnL", "CumulativePnL"]])
        
        # Daily summary
        daily = df.groupby("date").agg({
            "net_PnL": ["sum", "count"],
            "ExitReason": lambda x: x.value_counts().to_dict()
        }).reset_index()
        
        daily.columns = ["date", "net_PnL", "num_trades", "exit_reasons"]
        daily["CumulativePnL"] = daily["net_PnL"].cumsum()
        daily["winning_trades"] = df.groupby("date")["net_PnL"].apply(lambda x: (x > 0).sum()).values
        daily["losing_trades"] = df.groupby("date")["net_PnL"].apply(lambda x: (x < 0).sum()).values
        
        print("\n📈 Daily Summary:")
        print(daily[["date", "net_PnL", "num_trades", "winning_trades", "losing_trades", "CumulativePnL"]])
        
        # Performance metrics
        total_pnl = daily["net_PnL"].sum()
        avg_pnl = daily["net_PnL"].mean()
        win_rate = (daily["net_PnL"] > 0).mean() * 100
        sharpe = avg_pnl / daily["net_PnL"].std() if daily["net_PnL"].std() != 0 else 0
        max_dd = daily["CumulativePnL"].cummax().sub(daily["CumulativePnL"]).max()
        
        # Additional metrics
        total_trades = len(df)
        winning_trades = len(df[df["net_PnL"] > 0])
        losing_trades = len(df[df["net_PnL"] < 0])
        avg_win = df[df["net_PnL"] > 0]["net_PnL"].mean() if winning_trades > 0 else 0
        avg_loss = df[df["net_PnL"] < 0]["net_PnL"].mean() if losing_trades > 0 else 0
        max_win = df["net_PnL"].max()
        max_loss = df["net_PnL"].min()
        profit_factor = abs(df[df["net_PnL"] > 0]["net_PnL"].sum() / df[df["net_PnL"] < 0]["net_PnL"].sum()) if losing_trades > 0 else 0
        
        metrics = {
            "total_pnl": total_pnl,
            "avg_daily_pnl": avg_pnl,
            "win_rate": win_rate,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_win": max_win,
            "max_loss": max_loss,
            "profit_factor": profit_factor
        }
        
        print(f"\n✅ Total PnL: {total_pnl:.2f}")
        print(f"✅ Avg Daily PnL: {avg_pnl:.2f}")
        print(f"✅ Win Rate: {win_rate:.2f}%")
        print(f"✅ Sharpe Ratio (approx): {sharpe:.2f}")
        print(f"✅ Max Drawdown: {max_dd:.2f}")
        print(f"✅ Total Trades: {total_trades}")
        print(f"✅ Winning Trades: {winning_trades}")
        print(f"✅ Losing Trades: {losing_trades}")
        print(f"✅ Avg Win: {avg_win:.2f}")
        print(f"✅ Avg Loss: {avg_loss:.2f}")
        print(f"✅ Profit Factor: {profit_factor:.2f}")
        
        # Export to CSV
        if export_csv:
            self.export_summary_to_csv(daily, metrics)
        
        return df, daily, metrics
    
    def export_summary_to_csv(self, daily_df: pd.DataFrame, metrics: dict):
        """
        Export daily summary and metrics to CSV
        
        Parameters:
        -----------
        daily_df: Daily summary DataFrame
        metrics: Performance metrics dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export daily summary
        daily_filename = f"{self.output_dir}/daily_summary_{timestamp}.csv"
        daily_df.to_csv(daily_filename, index=False)
        print(f"\n✅ Daily summary exported to: {daily_filename}")
        
        # Export metrics
        metrics_filename = f"{self.output_dir}/performance_metrics_{timestamp}.csv"
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_csv(metrics_filename, index=False)
        print(f"✅ Performance metrics exported to: {metrics_filename}")
        
        return daily_filename, metrics_filename
    
    def get_intraday_pnl(self, date: str, reentry: int = 0, export_csv: bool = True):
        """
        Get minute-by-minute P&L for specific date and re-entry
        
        Parameters:
        -----------
        date: Date in YYYY-MM-DD format
        reentry: Re-entry number
        export_csv: If True, export to CSV
        
        Returns:
        --------
        DataFrame with intraday P&L
        """
        key = f"{date}_reentry_{reentry}"
        
        if key not in self.minute_pnl_records:
            print(f"⚠️ No intraday PnL found for {date} reentry {reentry}")
            return None
        
        intraday_df = self.minute_pnl_records[key].copy()
        
        # Export to CSV
        if export_csv:
            self.export_intraday_pnl_to_csv(intraday_df, date, reentry)
        
        return intraday_df
    
    def export_intraday_pnl_to_csv(self, df: pd.DataFrame, date: str, reentry: int):
        """
        Export intraday P&L to CSV
        
        Parameters:
        -----------
        df: Intraday P&L DataFrame
        date: Date in YYYY-MM-DD format
        reentry: Re-entry number
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/intraday_pnl_{date}_reentry{reentry}_{timestamp}.csv"
        
        # Format datetime
        export_df = df.copy()
        export_df["datetime"] = pd.to_datetime(export_df["datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        export_df.to_csv(filename, index=False)
        print(f"\n✅ Intraday P&L exported to: {filename}")
        
        return filename
    
    def export_all_intraday_pnl(self):
        """
        Export all intraday P&L records into a single combined CSV file
        (adds a 'key' column to identify each source DataFrame)
        """
        if not self.minute_pnl_records:
            print("⚠️ No intraday P&L records to export")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_data = []  # To hold all dataframes before concatenation

        for key, df in self.minute_pnl_records.items():
            if df.empty:
                continue
            
            export_df = df.copy()
            export_df["key"] = key  # 👈 Add key column
            export_df["datetime"] = pd.to_datetime(export_df["datetime"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            combined_data.append(export_df)

        # Concatenate all dataframes
        if not combined_data:
            print("⚠️ All P&L records were empty — nothing to export.")
            return

        final_df = pd.concat(combined_data, ignore_index=True)
        filename = f"{self.output_dir}/intraday_pnl_all_{timestamp}.csv"

        final_df.to_csv(filename, index=False)
        print(f"\n✅ Exported combined intraday P&L to: {filename}")
        print(f"📊 Total records: {len(final_df)} from {len(self.minute_pnl_records)} files.")


if __name__ == "__main__":
    # Load configuration
    config = StraddleConfig.from_yaml()
    
    # Initialize backtest engine
    engine = BacktestEngine(config)
    
    # Define backtest schedule
    symbol = "NIFTY"
    backtest_schedule = [
        ('2025-01-31', '2025-02-06'),
        ('2025-02-03', '2025-02-06'),
        ('2025-02-04', '2025-02-06'),
        ('2025-02-05', '2025-02-06'),
        ('2025-02-06', '2025-02-06'),
        ('2025-02-07', '2025-02-13'),
        ('2025-02-10', '2025-02-13'),
        ('2025-02-11', '2025-02-13'),
        ('2025-02-12', '2025-02-13'),
        ('2025-02-13', '2025-02-13'),
        ('2025-02-14', '2025-02-20'),
        ('2025-02-17', '2025-02-20'),
        ('2025-02-18', '2025-02-20'),
        ('2025-02-19', '2025-02-20'),
        ('2025-02-20', '2025-02-20'),
        ('2025-02-21', '2025-02-27'),
        ('2025-02-24', '2025-02-27'),
        ('2025-02-25', '2025-02-27'),
        ('2025-02-26', '2025-02-27'),
        ('2025-02-27', '2025-02-27'),
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



