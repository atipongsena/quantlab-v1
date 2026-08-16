"""Tests comparing simulation output with golden baseline."""

from pathlib import Path

from scripts.compare_golden import compare_directories


def test_golden_backtest_output_matches() -> None:
    actual = Path("artifacts/latest/backtest")
    golden = Path("artifacts/golden/synthetic_v1/backtest")

    if actual.exists() and golden.exists():
        code = compare_directories(actual, golden)
        assert code == 0
