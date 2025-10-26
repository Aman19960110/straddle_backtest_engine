# hyperparameter_optimizer.py

import itertools
import pandas as pd
from datetime import datetime
from app_config import StraddleConfig
from main import BacktestEngine


def evaluate_strategy(params, backtest_schedule, symbol="NIFTY"):
    """
    Runs backtest for a given parameter set and returns performance metrics.
    """
    print(f"\n🔍 Testing parameters: {params}")

    # Load base config
    config = StraddleConfig.from_yaml()

    # Dynamically set hyperparameters
    for key, value in params.items():
        setattr(config, key, value)

    # Initialize engine
    engine = BacktestEngine(config)

    # Run backtests
    for date, expiry in backtest_schedule:
        engine.run_backtest(symbol=symbol, expiry=expiry, dates=[date])

    # Generate summary metrics
    _, daily_df, metrics = engine.summary(export_csv=False)

    total_pnl = metrics.get("total_pnl", 0)
    sharpe = metrics.get("sharpe_ratio", 0)
    win_rate = metrics.get("win_rate", 0)
    profit_factor = metrics.get("profit_factor", 0)
    max_dd = metrics.get("max_drawdown", 0)

    print(f"✅ Completed | TotalPnL: {total_pnl:.2f} | Sharpe: {sharpe:.2f} | WinRate: {win_rate:.2f}% | MaxDD: {max_dd:.2f}")

    return total_pnl, sharpe, metrics


def grid_search(param_grid, backtest_schedule, symbol="NIFTY"):
    """
    Perform grid search over the given parameter grid.
    """
    all_combinations = list(itertools.product(*param_grid.values()))
    results = []

    print(f"\n🚀 Starting grid search: {len(all_combinations)} parameter combinations to test...\n")

    for combo in all_combinations:
        params = dict(zip(param_grid.keys(), combo))
        total_pnl, sharpe, metrics = evaluate_strategy(params, backtest_schedule, symbol)
        results.append({**params, "total_pnl": total_pnl, "sharpe_ratio": sharpe, **metrics})

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # ✅ Sort by Total PnL
    results_df = results_df.sort_values(by="total_pnl", ascending=False)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backtest_results/hyperparam_results_{timestamp}.csv"
    results_df.to_csv(filename, index=False)

    print(f"\n✅ Grid search complete. Results saved to {filename}")
    print("\n🏆 Top Configuration (by Total PnL):")
    print(results_df.iloc[0][['total_pnl', 'sharpe_ratio', 'win_rate', 'profit_factor', 'max_drawdown']])
    print(f"\nFull parameter set:\n{results_df.iloc[0].to_dict()}")

    return results_df


if __name__ == "__main__":
    # Define parameter grid
    param_grid = {
        "stop_loss_pct": [20,25],
        "target_profit_pct": [65,75],
        "max_reentries": [10],
        "reentry_delay_minutes": [5,10],
        "max_loss_per_day": [5000,10000],  
    }

    # Use a short period for tuning
    backtest_schedule = [
        ('2025-02-06', '2025-02-06'),
    ]

    results_df = grid_search(param_grid, backtest_schedule, symbol="NIFTY")

    print("\n🎯 Top 3 configurations (by Total PnL):")
    print(
        results_df.head(3)[
            [
                "total_pnl", "sharpe_ratio", "win_rate", "profit_factor", "stop_loss_pct",
                "target_profit_pct", "max_reentries", "reentry_delay_minutes", "max_loss_per_day"
            ]
        ]
    )
