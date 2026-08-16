"""Quantile segmentation and quantile return analytics."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping

from quantlab.domain.identity import InstrumentId


def assign_quantiles(
    scores: Mapping[InstrumentId, float],
    num_quantiles: int = 5,
) -> dict[InstrumentId, int]:
    """Assign instruments into discrete quantiles [1, num_quantiles] based on score.

    Ties broken deterministically by instrument_id string.
    Quantile 1 is lowest score, Quantile num_quantiles is highest score.
    """
    if not scores:
        return {}
    if num_quantiles <= 0:
        raise ValueError(f"num_quantiles must be positive, got {num_quantiles}")

    n = len(scores)
    # Sort deterministically: ascending score, then instrument_id string
    sorted_items = sorted(scores.items(), key=lambda item: (item[1], str(item[0].value)))

    assignments: dict[InstrumentId, int] = {}
    for rank_idx, (inst_id, _) in enumerate(sorted_items):
        # 1-indexed quantile from 1 to num_quantiles
        q = min(num_quantiles, int(math.floor(rank_idx * num_quantiles / n)) + 1)
        assignments[inst_id] = q

    return assignments


def compute_quantile_returns(
    quantiles: Mapping[InstrumentId, int],
    forward_returns: Mapping[InstrumentId, float],
    num_quantiles: int = 5,
) -> dict[int, float]:
    """Compute equal-weight mean forward return for each quantile."""
    buckets: dict[int, list[float]] = defaultdict(list)
    for inst_id, q in quantiles.items():
        ret = forward_returns.get(inst_id)
        if ret is not None and not math.isnan(ret) and not math.isinf(ret):
            buckets[q].append(ret)

    result: dict[int, float] = {}
    for q in range(1, num_quantiles + 1):
        vals = buckets.get(q, [])
        result[q] = sum(vals) / len(vals) if vals else 0.0

    return result
