"""Tests for portfolio weighting schemes."""

import uuid
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.portfolio.selection import SelectedAsset, SelectionReason
from quantlab.portfolio.weighting import EqualWeighting, InverseVolatilityWeighting


def test_equal_weighting_sums_to_exact_target() -> None:
    # 30 assets
    assets = [
        SelectedAsset(
            instrument_id=InstrumentId(uuid.UUID(int=i + 1)),
            rank=i + 1,
            score=float(30 - i),
            reason=SelectionReason.TOP_K_ENTRY,
        )
        for i in range(30)
    ]

    target_gross = Decimal("0.99")
    weighting = EqualWeighting()
    weights = weighting.compute_weights(assets, total_target_weight=target_gross)

    assert len(weights) == 30
    total_allocated = sum(weights.values())
    assert total_allocated == target_gross
    for w in weights.values():
        assert w > Decimal("0.0")


def test_inverse_volatility_weighting_sums_to_exact_target() -> None:
    assets = [
        SelectedAsset(
            instrument_id=InstrumentId(uuid.UUID(int=i + 1)),
            rank=i + 1,
            score=float(10 - i),
            reason=SelectionReason.TOP_K_ENTRY,
        )
        for i in range(10)
    ]
    # Volatilities from 0.10 to 0.50
    risk_metrics = {assets[i].instrument_id: 0.10 + 0.04 * i for i in range(10)}

    target_gross = Decimal("1.00")
    weighting = InverseVolatilityWeighting()
    weights = weighting.compute_weights(
        assets, total_target_weight=target_gross, risk_metrics=risk_metrics
    )

    assert len(weights) == 10
    total_allocated = sum(weights.values())
    assert total_allocated == target_gross

    # Lowest vol asset (rank 1) should have highest weight
    assert weights[assets[0].instrument_id] > weights[assets[-1].instrument_id]
