"""Tests for forward return labels and target construction."""

import uuid
from datetime import date

from quantlab.domain.identity import InstrumentId
from quantlab.ml.contracts import LabelSpec, LabelType
from quantlab.ml.labels import LabelCalculator


def test_label_calculator_computes_forward_returns() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    inst2 = InstrumentId(uuid.UUID(int=2))

    sessions = [date(2026, 1, i) for i in range(1, 10)]
    # Prices: inst1 grows 10% each session, inst2 flat
    prices = {s: {inst1: 100.0 * (1.10**i), inst2: 100.0} for i, s in enumerate(sessions)}

    # 2-session horizon
    spec = LabelSpec(horizon_sessions=2, label_type=LabelType.FORWARD_RETURN)
    labels = LabelCalculator.compute_forward_returns(prices, sessions, spec)

    # For session 0 (Jan 1): entry Jan 2 (i=1), exit Jan 4 (i=3)
    # expected return = (1.10^3 / 1.10^1) - 1 = 1.21 - 1 = 0.21
    s0 = sessions[0]
    assert s0 in labels
    assert abs(labels[s0][inst1] - 0.21) < 1e-4
    assert abs(labels[s0][inst2] - 0.0) < 1e-4
