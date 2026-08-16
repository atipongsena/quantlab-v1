"""Tests for cross-sectional factor transforms."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorValue, MissingReason
from quantlab.factors.transforms import (
    TransformSpec,
    rank_cross_section,
    robust_zscore_cross_section,
    transform_cross_section,
    winsorize_cross_section,
    zscore_cross_section,
)


def test_winsorize_cross_section() -> None:
    insts = [InstrumentId(uuid.uuid4()) for _ in range(100)]
    # Values from 0 to 99
    values = {inst: float(i) for i, inst in enumerate(insts)}

    # 1% / 99% winsorization
    winsorized = winsorize_cross_section(values, lower_quantile=0.05, upper_quantile=0.95)

    # Values below index 4 are clamped to 4.0, values above 95 clamped to 95.0
    assert winsorized[insts[0]] == 4.0
    assert winsorized[insts[99]] == 95.0
    assert winsorized[insts[50]] == 50.0


def test_rank_cross_section_with_ties() -> None:
    i1 = InstrumentId(uuid.uuid4())
    i2 = InstrumentId(uuid.uuid4())
    i3 = InstrumentId(uuid.uuid4())
    i4 = InstrumentId(uuid.uuid4())

    # Values with a tie: 10, 20, 20, 30
    values = {i1: 10.0, i2: 20.0, i3: 20.0, i4: 30.0}
    ranks_raw = rank_cross_section(values, normalize=False)

    assert ranks_raw[i1] == 1.0
    assert ranks_raw[i2] == 2.5  # average of ranks 2 and 3
    assert ranks_raw[i3] == 2.5
    assert ranks_raw[i4] == 4.0

    ranks_norm = rank_cross_section(values, normalize=True)
    assert ranks_norm[i1] == 0.0
    assert ranks_norm[i2] == 0.5
    assert ranks_norm[i3] == 0.5
    assert ranks_norm[i4] == 1.0


def test_zscore_and_robust_zscore() -> None:
    i1 = InstrumentId(uuid.uuid4())
    i2 = InstrumentId(uuid.uuid4())
    i3 = InstrumentId(uuid.uuid4())

    values = {i1: 1.0, i2: 2.0, i3: 3.0}
    z = zscore_cross_section(values)

    # mean=2.0, variance=(1+0+1)/3 = 2/3, std=sqrt(2/3) ~ 0.8165
    assert abs(z[i2]) < 1e-6
    assert abs(z[i1] + z[i3]) < 1e-6

    # Zero-variance protection
    constant_values = {i1: 5.0, i2: 5.0, i3: 5.0}
    z_const = zscore_cross_section(constant_values)
    assert all(val == 0.0 for val in z_const.values())

    robust_z = robust_zscore_cross_section(values)
    assert abs(robust_z[i2]) < 1e-6


def test_transform_cross_section_pipeline() -> None:
    i1 = InstrumentId(uuid.uuid4())
    i2 = InstrumentId(uuid.uuid4())
    i3 = InstrumentId(uuid.uuid4())

    input_values = {
        i1: FactorValue(instrument_id=i1, value=10.0),
        i2: FactorValue(instrument_id=i2, value=20.0),
        i3: FactorValue(
            instrument_id=i3, value=None, missing_reason=MissingReason.INSUFFICIENT_HISTORY
        ),
    }

    # Rank with direction = -1 (higher value -> lower rank score)
    spec = TransformSpec(rank=True, direction=-1)
    transformed = transform_cross_section(input_values, spec)

    assert transformed[i1].value == 1.0  # 1.0 - 0.0
    assert transformed[i2].value == 0.0  # 1.0 - 1.0
    assert transformed[i3].value is None
    assert transformed[i3].missing_reason == MissingReason.INSUFFICIENT_HISTORY
