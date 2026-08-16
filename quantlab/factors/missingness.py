"""Structured missingness rules and utilities for factors."""

from __future__ import annotations

import math
from collections.abc import Mapping

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorValue, MissingReason


def validate_denominator(
    denom: float | None,
    min_abs: float = 1e-6,
    require_positive: bool = False,
) -> bool:
    """Validate a denominator for financial factor calculations."""
    if denom is None or math.isnan(denom) or math.isinf(denom):
        return False
    if abs(denom) < min_abs:
        return False
    if require_positive and denom <= 0:
        return False
    return True


def check_history_length(
    actual_length: int,
    required_length: int,
) -> MissingReason | None:
    """Check whether actual history meets the required lookback."""
    if actual_length < required_length:
        return MissingReason.INSUFFICIENT_HISTORY
    return None


def partition_valid_values(
    values: Mapping[InstrumentId, FactorValue | float | None],
) -> tuple[dict[InstrumentId, float], dict[InstrumentId, MissingReason]]:
    """Partition input values into valid numeric float mappings and missing reasons."""
    valid: dict[InstrumentId, float] = {}
    missing: dict[InstrumentId, MissingReason] = {}

    for inst, val in values.items():
        if val is None:
            missing[inst] = MissingReason.INSUFFICIENT_HISTORY
        elif isinstance(val, FactorValue):
            if val.is_valid and val.value is not None:
                if math.isnan(val.value) or math.isinf(val.value):
                    missing[inst] = MissingReason.OUT_OF_RANGE
                else:
                    valid[inst] = float(val.value)
            else:
                missing[inst] = val.missing_reason or MissingReason.INSUFFICIENT_HISTORY
        else:
            v_float = float(val)
            if math.isnan(v_float) or math.isinf(v_float):
                missing[inst] = MissingReason.OUT_OF_RANGE
            else:
                valid[inst] = v_float

    return valid, missing
