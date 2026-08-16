"""Tests for execution friction stress testing."""

from quantlab.validation.execution_stress import ExecutionStressTester


def test_execution_stress_break_even_calculation() -> None:
    # 20% gross return with 200% annual turnover (2.0)
    # Total roundtrip volume = 4.0
    # Cost per 10 bps = 4.0 * 0.0010 = 0.0040 (0.4% drag)
    # Break even = 0.20 / (2.0 * 2) * 10000 = 500 bps
    res = ExecutionStressTester.evaluate(
        zero_cost_cagr=0.20,
        turnover_annual=2.0,
    )
    assert not res.is_cost_fragile
    assert res.break_even_cost_bps == 500.0


def test_execution_stress_fragile_high_turnover_strategy() -> None:
    # 2% gross return with 2000% annual turnover (20.0) -> fragile edge
    res = ExecutionStressTester.evaluate(
        zero_cost_cagr=0.02,
        turnover_annual=20.0,
    )
    assert res.is_cost_fragile
    assert res.break_even_cost_bps < 10.0
