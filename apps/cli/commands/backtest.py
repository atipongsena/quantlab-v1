"""CLI command handlers for backtesting."""

from __future__ import annotations

import argparse
import json
from datetime import date

from quantlab.application.backtests import BacktestService


def run_backtest(args: argparse.Namespace) -> int:
    service = BacktestService()

    start_date = date.fromisoformat(args.start) if getattr(args, "start", None) else None
    end_date = date.fromisoformat(args.end) if getattr(args, "end", None) else None

    result = service.run_backtest(
        strategy_config_path=args.config,
        dataset_id=getattr(args, "dataset", "DATASET-v001"),
        start_date=start_date,
        end_date=end_date,
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print(f"Backtest Execution Report: {result.spec.strategy_id}")
    spec = result.spec
    print(
        f"Period: {spec.start_session} to {spec.end_session} "
        f"(Initial Cash: ${spec.initial_cash:,.2f})"
    )
    print("=" * 70)
    m = result.metrics
    print(f"Total Return       : {m.total_return * 100:+.2f}%")
    print(f"CAGR               : {m.cagr * 100:+.2f}%")
    print(f"Annual Volatility  : {m.annualized_volatility * 100:.2f}%")
    print(f"Sharpe Ratio       : {m.sharpe_ratio:+.2f}")
    print(f"Sortino Ratio      : {m.sortino_ratio:+.2f}")
    print(f"Max Drawdown       : {m.max_drawdown * 100:.2f}% ({m.max_drawdown_duration_days} days)")
    print(f"Calmar Ratio       : {m.calmar_ratio:+.2f}")
    print(f"Win Rate           : {m.win_rate * 100:.1f}%")
    print(f"Profit Factor      : {m.profit_factor:.2f}")
    print(f"Total Turnover     : {m.total_turnover * 100:.1f}%")
    print(f"Total Fees         : ${m.total_fees:,.2f}")
    print(f"Total Slippage     : ${m.total_slippage:,.2f}")

    comparison = service.last_benchmark_comparison
    if comparison is not None:
        print("-" * 70)
        print(f"Versus {comparison.benchmark_symbol} (buy and hold, total return)")
        print(
            f"  Benchmark CAGR   : {comparison.benchmark_cagr * 100:+.2f}%   "
            f"Strategy CAGR: {comparison.strategy_cagr * 100:+.2f}%"
        )
        print(
            f"  Beta             : {comparison.beta:.2f}        "
            f"Correlation : {comparison.correlation:.2f}"
        )
        print(f"  Annualized alpha : {comparison.annualized_alpha * 100:+.2f}% (Jensen)")
        print(
            f"  Tracking error   : {comparison.tracking_error * 100:.2f}%   "
            f"Information ratio: {comparison.information_ratio:+.2f}"
        )

    print("=" * 70)
    print(f"Status: PASS [Hash: {result.content_hash[:16]}...]")

    return 0
