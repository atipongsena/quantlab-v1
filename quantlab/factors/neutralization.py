"""Sector and industry neutralization for cross-sectional factor scores."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from quantlab.domain.identity import InstrumentId
from quantlab.factors.transforms import rank_cross_section


def neutralize_within_groups(
    values: Mapping[InstrumentId, float],
    groups: Mapping[InstrumentId, str],
    normalize_rank: bool = True,
) -> dict[InstrumentId, float]:
    """Perform rank transform independently within each group/sector."""
    if not values:
        return {}

    # Group instruments
    group_map: dict[str, dict[InstrumentId, float]] = defaultdict(dict)
    for inst, val in values.items():
        group_name = groups.get(inst, "UNKNOWN")
        group_map[group_name][inst] = val

    result: dict[InstrumentId, float] = {}
    for _, group_vals in group_map.items():
        ranked_group = rank_cross_section(group_vals, normalize=normalize_rank)
        result.update(ranked_group)

    return result


def neutralize_by_ols_residuals(
    values: Mapping[InstrumentId, float],
    groups: Mapping[InstrumentId, str],
) -> dict[InstrumentId, float]:
    """Neutralize factor scores against categorical sector dummies using OLS residuals.

    Residual for each group member is: x_i - mean(x_group).
    This mathematically equals the OLS residual against one-hot sector indicators.
    """
    if not values:
        return {}

    group_map: dict[str, list[tuple[InstrumentId, float]]] = defaultdict(list)
    for inst, val in values.items():
        group_name = groups.get(inst, "UNKNOWN")
        group_map[group_name].append((inst, val))

    residuals: dict[InstrumentId, float] = {}
    for _, group_items in group_map.items():
        mean_group = sum(val for _, val in group_items) / len(group_items)
        for inst, val in group_items:
            residuals[inst] = val - mean_group

    return residuals
