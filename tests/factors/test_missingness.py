"""Tests for factor missingness logic."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorValue, MissingReason
from quantlab.factors.missingness import (
    check_history_length,
    partition_valid_values,
    validate_denominator,
)


def test_validate_denominator() -> None:
    assert validate_denominator(100.0) is True
    assert validate_denominator(-50.0) is True
    assert validate_denominator(0.0) is False
    assert validate_denominator(1e-7) is False
    assert validate_denominator(None) is False
    assert validate_denominator(float("nan")) is False
    assert validate_denominator(float("inf")) is False

    # Positive requirement
    assert validate_denominator(-50.0, require_positive=True) is False
    assert validate_denominator(50.0, require_positive=True) is True


def test_check_history_length() -> None:
    assert check_history_length(252, 252) is None
    assert check_history_length(100, 252) == MissingReason.INSUFFICIENT_HISTORY


def test_partition_valid_values() -> None:
    i1 = InstrumentId(uuid.uuid4())
    i2 = InstrumentId(uuid.uuid4())
    i3 = InstrumentId(uuid.uuid4())
    i4 = InstrumentId(uuid.uuid4())

    values = {
        i1: FactorValue(instrument_id=i1, value=0.25),
        i2: FactorValue(
            instrument_id=i2, value=None, missing_reason=MissingReason.MISSING_FUNDAMENTAL
        ),
        i3: None,
        i4: float("nan"),
    }

    valid, missing = partition_valid_values(values)
    assert valid == {i1: 0.25}
    assert missing[i2] == MissingReason.MISSING_FUNDAMENTAL
    assert missing[i3] == MissingReason.INSUFFICIENT_HISTORY
    assert missing[i4] == MissingReason.OUT_OF_RANGE
