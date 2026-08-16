"""Tests for performance metrics and risk calculator."""

from decimal import Decimal

from quantlab.analytics.performance import PerformanceCalculator


def test_performance_calculator_returns_and_drawdown() -> None:
    # 5-session equity curve: 100, 105, 102, 108, 110 (+10% total return)
    equity = [
        Decimal("100.00"),
        Decimal("105.00"),
        Decimal("102.00"),
        Decimal("108.00"),
        Decimal("110.00"),
    ]

    metrics = PerformanceCalculator.calculate(equity_series=equity)

    assert metrics.total_return == 0.10
    assert metrics.cagr > 0.0
    assert metrics.annualized_volatility > 0.0
    assert metrics.sharpe_ratio > 0.0
    # Peak is 105, drops to 102 -> DD = (105 - 102)/105 = 3/105 ~= 2.857%
    assert round(metrics.max_drawdown, 4) == round(3.0 / 105.0, 4)
    assert metrics.win_rate == 0.75  # 3 wins out of 4 daily returns
    assert metrics.profit_factor > 1.0


def test_performance_calculator_zero_or_negative_returns() -> None:
    equity = [Decimal("100.00"), Decimal("90.00")]
    metrics = PerformanceCalculator.calculate(equity_series=equity)

    assert metrics.total_return == -0.10
    assert metrics.max_drawdown == 0.10
    assert metrics.win_rate == 0.0
    assert metrics.profit_factor == 0.0
