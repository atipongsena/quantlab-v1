"""Train-only preprocessing and normalization to eliminate lookahead leakage."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreprocessorState:
    means: tuple[float, ...]
    stds: tuple[float, ...]
    p01: tuple[float, ...]
    p99: tuple[float, ...]


class TrainOnlyPreprocessor:
    """Standardizer and winsorizer fitted strictly on training data."""

    def __init__(self, state: PreprocessorState | None = None) -> None:
        self._state = state

    @property
    def is_fitted(self) -> bool:
        return self._state is not None

    @classmethod
    def fit(cls, X: Sequence[Sequence[float]]) -> TrainOnlyPreprocessor:
        if not X or not X[0]:
            raise ValueError("Input feature matrix X cannot be empty")

        n_samples = len(X)
        n_features = len(X[0])

        means: list[float] = []
        stds: list[float] = []
        p01_list: list[float] = []
        p99_list: list[float] = []

        for j in range(n_features):
            vals = [row[j] for row in X]
            sorted_vals = sorted(vals)

            # Winsorization cutoffs
            p01_idx = max(0, int(0.01 * n_samples))
            p99_idx = min(n_samples - 1, int(0.99 * n_samples))
            p01 = sorted_vals[p01_idx]
            p99 = sorted_vals[p99_idx]

            clipped = [min(max(v, p01), p99) for v in vals]
            mean = sum(clipped) / n_samples
            var = sum((v - mean) ** 2 for v in clipped) / (n_samples - 1 if n_samples > 1 else 1)
            std = math.sqrt(var) if var > 1e-8 else 1.0

            means.append(mean)
            stds.append(std)
            p01_list.append(p01)
            p99_list.append(p99)

        state = PreprocessorState(
            means=tuple(means),
            stds=tuple(stds),
            p01=tuple(p01_list),
            p99=tuple(p99_list),
        )
        return cls(state)

    def transform(self, X: Sequence[Sequence[float]]) -> list[list[float]]:
        if self._state is None:
            raise RuntimeError("Preprocessor must be fitted before transforming")

        transformed: list[list[float]] = []
        for row in X:
            t_row: list[float] = []
            for j, val in enumerate(row):
                # Clip to train-fitted percentiles
                clipped = min(max(val, self._state.p01[j]), self._state.p99[j])
                std = self._state.stds[j]
                scaled = (clipped - self._state.means[j]) / std if std > 1e-8 else 0.0
                t_row.append(scaled)
            transformed.append(t_row)

        return transformed
