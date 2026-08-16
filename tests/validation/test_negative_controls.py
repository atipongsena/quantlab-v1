"""Tests for negative controls (label shuffle and noise factor)."""

import uuid
from datetime import date

from quantlab.domain.identity import InstrumentId
from quantlab.validation.negative_controls import NegativeControlRunner


def test_label_shuffle_collapses_rank_correlation() -> None:
    # Strongly positive true signal
    insts = [InstrumentId(uuid.UUID(int=i)) for i in range(1, 51)]
    factor_scores = {inst: float(i) for i, inst in enumerate(insts)}
    true_returns = {inst: float(i) * 0.01 for i, inst in enumerate(insts)}

    # Shuffled returns collapse correlation
    shuffled_ic = NegativeControlRunner.run_label_shuffle(
        factor_scores=factor_scores,
        forward_returns=true_returns,
        seed=123,
    )
    assert abs(shuffled_ic) < 0.35


def test_noise_factor_generation() -> None:
    insts = [InstrumentId(uuid.UUID(int=i)) for i in range(1, 21)]
    snap = NegativeControlRunner.generate_noise_factor(insts, date(2026, 1, 2), seed=42)

    assert snap.factor_id == "noise_control"
    assert len(snap.values) == 20
