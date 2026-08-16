"""Negative control experiments (label shuffles and noise factors)."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue


class NegativeControlRunner:
    """Runs negative controls to detect structural false positives."""

    @classmethod
    def run_label_shuffle(
        cls,
        factor_scores: Mapping[InstrumentId, float],
        forward_returns: Mapping[InstrumentId, float],
        seed: int = 42,
    ) -> float:
        """Evaluates Spearman rank correlation after randomly permuting returns."""
        common = sorted(
            set(factor_scores.keys()) & set(forward_returns.keys()),
            key=lambda x: str(x.value),
        )
        if len(common) < 5:
            return 0.0

        scores = [factor_scores[i] for i in common]
        rets = [forward_returns[i] for i in common]

        rng = random.Random(seed)
        shuffled_rets = list(rets)
        rng.shuffle(shuffled_rets)

        # Compute rank IC
        n = len(common)
        rank_s = [sorted(scores).index(x) + 1 for x in scores]
        rank_r = [sorted(shuffled_rets).index(y) + 1 for y in shuffled_rets]

        mean_s = sum(rank_s) / n
        mean_r = sum(rank_r) / n

        cov = sum((rank_s[i] - mean_s) * (rank_r[i] - mean_r) for i in range(n))
        std_s = math.sqrt(sum((x - mean_s) ** 2 for x in rank_s))
        std_r = math.sqrt(sum((y - mean_r) ** 2 for y in rank_r))

        return cov / (std_s * std_r) if (std_s * std_r) > 1e-8 else 0.0

    @classmethod
    def generate_noise_factor(
        cls,
        universe: Sequence[InstrumentId],
        session: date,
        seed: int = 42,
    ) -> FactorSnapshot:
        """Generates a pure Gaussian white noise factor snapshot."""
        rng = random.Random(seed)
        values = {
            inst: FactorValue(instrument_id=inst, value=rng.gauss(0.0, 1.0)) for inst in universe
        }
        return FactorSnapshot.create(
            factor_id="noise_control",
            version="v1",
            session=session,
            as_of=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
            values=values,
        )
