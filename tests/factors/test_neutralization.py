"""Tests for sector and industry neutralization."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.factors.neutralization import (
    neutralize_by_ols_residuals,
    neutralize_within_groups,
)


def test_neutralize_within_groups() -> None:
    t1 = InstrumentId(uuid.uuid4())
    t2 = InstrumentId(uuid.uuid4())
    f1 = InstrumentId(uuid.uuid4())
    f2 = InstrumentId(uuid.uuid4())

    values = {t1: 10.0, t2: 20.0, f1: 100.0, f2: 200.0}
    sectors = {t1: "TECH", t2: "TECH", f1: "FIN", f2: "FIN"}

    ranked = neutralize_within_groups(values, sectors, normalize_rank=True)

    # Within TECH: t1 is 0.0, t2 is 1.0
    assert ranked[t1] == 0.0
    assert ranked[t2] == 1.0

    # Within FIN: f1 is 0.0, f2 is 1.0
    assert ranked[f1] == 0.0
    assert ranked[f2] == 1.0


def test_neutralize_by_ols_residuals() -> None:
    t1 = InstrumentId(uuid.uuid4())
    t2 = InstrumentId(uuid.uuid4())
    u1 = InstrumentId(uuid.uuid4())

    values = {t1: 10.0, t2: 20.0, u1: 50.0}
    sectors = {t1: "TECH", t2: "TECH"}  # u1 is UNKNOWN

    residuals = neutralize_by_ols_residuals(values, sectors)

    # TECH mean is 15.0 -> residuals: t1=-5.0, t2=5.0
    assert residuals[t1] == -5.0
    assert residuals[t2] == 5.0

    # UNKNOWN mean is 50.0 -> residual: 0.0
    assert residuals[u1] == 0.0
