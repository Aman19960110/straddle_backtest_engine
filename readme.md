# straddle_backtest_engine

A modular backtesting engine for straddle option strategies focused on Indian derivatives (NSE). It provides a configurable framework to run single backtests, record results, and perform hyperparameter tuning.

---

## 🚀 Features

- Modular and easy-to-extend design for options backtesting
- YAML-based configuration management (`StraddleConfig`)
- Hyperparameter tuning framework for strategy optimization
- Supports custom connectors and data loaders (like BreezeDataConnector)
- Clean exports for trades, results, and summaries

---

## 📁 Repository Structure

```
straddle_backtest_engine/
├── app_config/            # Configuration files and YAML settings
├── backtest_results/      # Output of backtests (PnL, logs, summaries)
├── data/                  # Input market data (NSE options/futures)
├── logs/                  # Runtime logs
├── strategy/              # Strategy implementations
├── utils/                 # Helper functions (data, metrics, etc.)
├── main.py                # Main entrypoint for running a backtest
├── hyperparameter_tuning.py
├── pyproject.toml or setup.py
└── README.md
```

---

## ⚙️ Installation

You can install the repo directly using `pip`:

```bash
pip install git+https://github.com/Aman19960110/straddle_backtest_engine.git
```

Or clone it for local development:

```bash
git clone https://github.com/Aman19960110/straddle_backtest_engine.git
cd straddle_backtest_engine
pip install -e .
```

---

## 🧾 Configuration Setup (Important)

Before running any backtest, you need to create a **YAML configuration file** for your strategy.

### Step 1: Create a credentials file
Create a file named `credentials.yml` inside your working directory (for example `/content/credentials.yml` if you’re using Google Colab):

```yaml
symbol: "NIFTY"
underlying: "NIFTY"
exchange: "NFO"
expiry: "2025-11-07"
lot_size: 50

market_open: "09:15"
market_close: "15:30"

max_loss_per_day: 12000
stop_loss_pct: 25
target_profit_pct: 75
max_reentries: 10
reentry_delay_minutes: 10
```

### Step 2: Pass it to the configuration loader
```python
from app_config.app_config import StraddleConfig

config = StraddleConfig.from_yaml('/content/credentials.yml')
```

This loads your parameters into the engine.

---

## 🧠 Example: Initializing and Running a Backtest

Here’s a typical workflow you can follow (as shown in your screenshot):

```python
# Install (only once)
!pip install git+https://github.com/Aman19960110/straddle_backtest_engine.git

# Import core modules
from app_config.app_config import StraddleConfig
from data.breeze_connector import BreezeDataConnector
from data.data_loader import DataLoader
from strategy.straddle_strategy import StraddleStrategy
from engine.engine import BacktestEngine

import pandas as pd
import numpy as np
import time

# Define run parameters
symbol = 'NIFTY'
expiry = '2025-10-28'
dates = ['2025-10-28']

# Initialize engine
config = StraddleConfig.from_yaml('/content/credentials.yml')
engine = BacktestEngine(config)

# Run backtest
engine.run_backtest(symbol=symbol, expiry=expiry, dates=dates)
```

---

## 🔁 For Multiple Days or Expiries

```python
for date, expiry in backtest_schedule:
    print(f"\n🚀 Running backtest for {date} | Expiry {expiry}")
    engine.run_backtest(symbol=symbol, expiry=expiry, dates=[date])

# Export combined results
if engine.results:
    combined_df = pd.DataFrame(engine.results)
    print(f"\n✅ Total Trades: {len(combined_df)} across {len(backtest_schedule)} sessions")

    # Save consolidated report
    engine.export_results_to_csv(combined_df)
    engine.summary(export_csv=True)
    engine.export_all_intraday_pnl()

    print("\n📊 Consolidated report generated in 'backtest_results/' folder")
else:
    print("⚠️ No trades found — check data or strategy settings.")
```

---

## 📊 Output and Results

- All generated reports, trade logs, and summaries are stored in the `backtest_results/` folder.
- Logs for each run are stored under `logs/`.
- You can load and analyze results later using pandas.

---

## 🧠 Hyperparameter Tuning

Use the built-in script to run multiple combinations of parameters:

```bash
python hyperparameter_tuning.py
```

You can define parameter grids such as:
```python
param_grid = {
    'stop_loss_pct': [20, 25, 30],
    'target_profit_pct': [65, 75, 85],
    'max_reentries': [7, 10, 13],
    'reentry_delay_minutes': [5, 10, 15]
}
```
The engine will iterate over all combinations and store results for comparison.

---

## 🧩 Tips for Development

- Always check that your YAML file path is correct when running in Google Colab or a virtual environment.
- You can pass a relative path or absolute path to `StraddleConfig.from_yaml()`.
- To improve speed during hyperparameter tuning, parallelize using `multiprocessing` or `joblib`.

---

## 📬 Contact

**Author:** Aman19960110  
For contributions or issues, open a GitHub issue or PR.

---

Would you like me to add an **example YAML** and **sample Colab notebook** to the repo so others can reproduce this workflow easily?

