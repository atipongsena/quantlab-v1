"""False Discovery Rate (FDR) multiple testing adjustments (Benjamini-Hochberg)."""

from __future__ import annotations

from collections.abc import Sequence


class BenjaminiHochbergFDR:
    """Controls False Discovery Rate across multiple factor hypotheses."""

    @classmethod
    def adjust(
        cls,
        p_values: Sequence[float],
        alpha: float = 0.05,
    ) -> tuple[bool, ...]:
        """Returns boolean tuple indicating whether each hypothesis is statistically significant."""
        m = len(p_values)
        if m == 0:
            return ()

        # Pair with original indices
        indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])

        # Find largest k such that p_(k) <= (k / m) * alpha
        max_k = -1
        for rank, (orig_idx, p_val) in enumerate(indexed_p, start=1):
            threshold = (float(rank) / float(m)) * alpha
            if p_val <= threshold:
                max_k = rank

        # Hypotheses with rank <= max_k are significant discoveries
        significant = [False] * m
        if max_k != -1:
            for rank in range(max_k):
                orig_idx = indexed_p[rank][0]
                significant[orig_idx] = True

        return tuple(significant)
