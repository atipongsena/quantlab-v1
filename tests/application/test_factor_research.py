"""Tests for FactorResearchService application workflows."""

from datetime import date
from pathlib import Path

import pytest

from quantlab.application.factor_research import FactorResearchService
from quantlab.data.datasets import DatasetNotFoundError


def test_factor_research_service_list() -> None:
    service = FactorResearchService()
    factors = service.list_factors()
    assert len(factors) >= 14
    ids = {f["factor_id"] for f in factors}
    assert "momentum_12_1" in ids
    assert "roe" in ids
    assert "volatility_60d" in ids
    assert "earnings_yield" in ids


def test_factor_research_service_run_pipeline(synthetic_workspace: Path) -> None:
    """The pipeline must produce a populated report from a real published dataset."""
    service = FactorResearchService(base_dir=synthetic_workspace)
    result = service.run_factor_research(
        factor_id="momentum_12_1",
        dataset_id="DATASET-v001",
        start_date=date(2021, 1, 1),
        end_date=date(2022, 12, 31),
    )

    assert result.factor_id == "momentum_12_1"
    assert result.diagnostic_label == "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"
    assert result.num_sessions > 12, "expected a monthly rebalance grid across two years"
    assert result.breadth_mean > 0, "no instrument had both a score and a forward return"
    assert -1.0 <= result.rank_ic_mean <= 1.0
    assert set(result.decay_profile) == {"1M", "3M", "6M", "12M"}


def test_etfs_are_excluded_from_the_equity_cross_section(synthetic_workspace: Path) -> None:
    """SPY sits in the fixture as a benchmark and must not be ranked against equities."""
    service = FactorResearchService(base_dir=synthetic_workspace)
    equities = service._get_universe("DATASET-v001")
    symbols = {member.symbol for member in equities}

    assert "SPY" not in symbols
    assert "AAPL" in symbols


def test_unbuilt_dataset_fails_loudly(synthetic_workspace: Path) -> None:
    """Asking for a dataset that was never built must raise, not return empty results.

    Silently returning zeros here is how a broken pipeline reports a clean bill of
    health for months.
    """
    service = FactorResearchService(base_dir=synthetic_workspace)
    with pytest.raises(DatasetNotFoundError):
        service.run_factor_research(
            factor_id="momentum_12_1",
            dataset_id="DATASET-DOES-NOT-EXIST",
        )
