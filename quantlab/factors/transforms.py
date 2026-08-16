"""Deterministic cross-sectional factor transforms."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorValue
from quantlab.factors.missingness import partition_valid_values


@dataclass(frozen=True, slots=True)
class TransformSpec:
    winsorize: bool = False
    lower_quantile: float = 0.01
    upper_quantile: float = 0.99
    rank: bool = False
    zscore: bool = False
    robust_zscore: bool = False
    direction: int = 1


def winsorize_cross_section(
    values: Mapping[InstrumentId, float],
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> dict[InstrumentId, float]:
    """Winsorize cross-sectional values at specified quantiles."""
    if not values:
        return {}
    if len(values) < 3:
        return dict(values)

    sorted_vals = sorted(values.values())
    n = len(sorted_vals)

    lower_idx = int(math.floor(lower_quantile * (n - 1)))
    upper_idx = int(math.ceil(upper_quantile * (n - 1)))

    lower_bound = sorted_vals[max(0, min(lower_idx, n - 1))]
    upper_bound = sorted_vals[max(0, min(upper_idx, n - 1))]

    return {inst: max(lower_bound, min(upper_bound, val)) for inst, val in values.items()}


def rank_cross_section(
    values: Mapping[InstrumentId, float],
    normalize: bool = True,
) -> dict[InstrumentId, float]:
    """Compute percentile ranks with deterministic average tie-breaking.

    If normalize=True, scales output to [0.0, 1.0].
    """
    if not values:
        return {}
    n = len(values)
    if n == 1:
        inst = next(iter(values))
        return {inst: 0.5 if normalize else 1.0}

    # Group instruments by value
    val_groups: dict[float, list[InstrumentId]] = defaultdict(list)
    # Sort items deterministically by value then instrument_id string
    sorted_items = sorted(values.items(), key=lambda item: (item[1], str(item[0].value)))

    for inst, val in sorted_items:
        val_groups[val].append(inst)

    ranks: dict[InstrumentId, float] = {}
    current_rank = 1
    for val, inst_list in sorted(val_groups.items(), key=lambda item: item[0]):
        group_len = len(inst_list)
        # Average rank for ties: sum(current_rank + i for i in range(group_len)) / group_len
        avg_rank = current_rank + (group_len - 1) / 2.0
        for inst in inst_list:
            if normalize:
                # Standard percentile rank in [0, 1]: (avg_rank - 1) / (n - 1)
                ranks[inst] = (avg_rank - 1.0) / (n - 1.0)
            else:
                ranks[inst] = avg_rank
        current_rank += group_len

    return ranks


def zscore_cross_section(
    values: Mapping[InstrumentId, float],
    ddof: int = 0,
) -> dict[InstrumentId, float]:
    """Compute cross-sectional Z-scores: (x - mean) / std."""
    if not values:
        return {}
    n = len(values)
    if n == 1:
        inst = next(iter(values))
        return {inst: 0.0}

    vals = list(values.values())
    mean_val = sum(vals) / n
    variance = sum((x - mean_val) ** 2 for x in vals) / max(1, n - ddof)
    std_val = math.sqrt(variance)

    if std_val < 1e-12:
        return {inst: 0.0 for inst in values}

    return {inst: (val - mean_val) / std_val for inst, val in values.items()}


def robust_zscore_cross_section(
    values: Mapping[InstrumentId, float],
) -> dict[InstrumentId, float]:
    """Compute robust Z-score using median and median absolute deviation (MAD)."""
    if not values:
        return {}
    n = len(values)
    if n == 1:
        inst = next(iter(values))
        return {inst: 0.0}

    sorted_vals = sorted(values.values())
    if n % 2 == 1:
        median_val = sorted_vals[n // 2]
    else:
        median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    abs_deviations = sorted(abs(x - median_val) for x in sorted_vals)
    if n % 2 == 1:
        mad = abs_deviations[n // 2]
    else:
        mad = (abs_deviations[n // 2 - 1] + abs_deviations[n // 2]) / 2.0

    # Normal consistency factor 1.4826
    normal_mad = 1.4826 * mad

    if normal_mad < 1e-12:
        return zscore_cross_section(values)

    return {inst: (val - median_val) / normal_mad for inst, val in values.items()}


def transform_cross_section(
    values: Mapping[InstrumentId, FactorValue | float | None],
    spec: TransformSpec,
) -> dict[InstrumentId, FactorValue]:
    """Apply configured cross-sectional transforms preserving missingness reasons."""
    valid_map, missing_map = partition_valid_values(values)
    current_transformed = dict(valid_map)

    if current_transformed:
        if spec.winsorize:
            current_transformed = winsorize_cross_section(
                current_transformed,
                lower_quantile=spec.lower_quantile,
                upper_quantile=spec.upper_quantile,
            )

        if spec.rank:
            current_transformed = rank_cross_section(current_transformed, normalize=True)
        elif spec.robust_zscore:
            current_transformed = robust_zscore_cross_section(current_transformed)
        elif spec.zscore:
            current_transformed = zscore_cross_section(current_transformed)

        if spec.direction == -1:
            if spec.rank:
                current_transformed = {inst: 1.0 - val for inst, val in current_transformed.items()}
            else:
                current_transformed = {inst: -val for inst, val in current_transformed.items()}

    output: dict[InstrumentId, FactorValue] = {}
    for inst, val in current_transformed.items():
        output[inst] = FactorValue(instrument_id=inst, value=val, missing_reason=None)

    for inst, reason in missing_map.items():
        output[inst] = FactorValue(instrument_id=inst, value=None, missing_reason=reason)

    return output
