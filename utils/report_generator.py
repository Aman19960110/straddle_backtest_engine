# utils/report_generator.py

import pandas as pd
import quantstats as qs
import yfinance as yf
import os

def generate_report(backtest_csv_path: str,
                    initial_capital: float = 400000, rf_rate: float = 0.06):
    """
    Generate QuantStats performance report comparing strategy vs NIFTY.

    Parameters
    ----------
    backtest_csv_path : str
        Path to CSV file containing backtest results (with 'date', 'net_PnL', 'gross_pnl').
    start_date : str
        Start date for benchmark (format 'YYYY-MM-DD').
    end_date : str
        End date for benchmark.
    initial_capital : float
        Starting capital for cumulative P&L.
    rf_rate : float
        Annualized risk-free rate (e.g. 0.06 = 6%).

    Output
    ------
    HTML report saved to 'backtest_results/net_returns_report.html'.
    """
    # ===============================
    # 📊 Load NIFTY benchmark data
    # ===============================
    data = pd.read_csv(backtest_csv_path, parse_dates=["date"], index_col="date")
    start_date = data.index[0].strftime('%Y-%m-%d')
    end_date = data.index[-1].strftime('%Y-%m-%d')


    print("📥 Downloading NIFTY benchmark data...")
    nifty = yf.download("^NSEI", start=start_date, end=end_date)
    nifty_returns = nifty["Close"].pct_change().dropna()

    # ===============================
    # 📄 Load backtest results
    # ===============================
    print(f"📂 Reading backtest CSV: {backtest_csv_path}")
    

    # Ensure columns exist
    if not all(col in data.columns for col in ["net_PnL", "gross_pnl"]):
        raise ValueError("CSV must contain 'net_PnL' and 'gross_pnl' columns")

    # ===============================
    # 💰 Compute daily cumulative PnL
    # ===============================
    daily_pnl = data.groupby(data.index)[["net_PnL", "gross_pnl"]].sum()
    daily_pnl = daily_pnl.cumsum() + initial_capital

    # Convert to daily returns
    net_returns = daily_pnl["net_PnL"].pct_change().dropna()
    gross_returns = daily_pnl["gross_pnl"].pct_change().dropna()

    # ===============================
    # 📈 Generate QuantStats Report
    # ===============================
    qs.extend_pandas()

    output_dir = "backtest_results"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "net_returns_report.html")

    print("🧮 Generating QuantStats performance report...")
    qs.reports.html(
        net_returns,
        benchmark=nifty_returns,
        rf=rf_rate,
        output=output_path,
        title="Straddle Strategy Performance vs NIFTY"
    )

    print(f"\n✅ Report generated successfully: {output_path}")
