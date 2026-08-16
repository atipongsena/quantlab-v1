"""Deterministic pure-Python Ridge linear regressor and cross-sectional ranker."""

from __future__ import annotations

from collections.abc import Sequence


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Solves A x = b using Gaussian elimination with partial pivoting in pure Python."""
    n = len(A)
    # Augmented matrix [A | b]
    M = [A[i][:] + [b[i]] for i in range(n)]

    for i in range(n):
        # Find pivot row
        max_row = i
        max_val = abs(M[i][i])
        for r in range(i + 1, n):
            if abs(M[r][i]) > max_val:
                max_val = abs(M[r][i])
                max_row = r

        if max_val < 1e-12:
            # Singular / near-singular matrix -> regularize diagonal
            M[i][i] += 1e-6

        # Swap rows
        M[i], M[max_row] = M[max_row], M[i]

        # Eliminate below
        pivot = M[i][i]
        for r in range(i + 1, n):
            factor = M[r][i] / pivot
            for c in range(i, n + 1):
                M[r][c] -= factor * M[i][c]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        total = M[i][n]
        for c in range(i + 1, n):
            total -= M[i][c] * x[c]
        x[i] = total / M[i][i]

    return x


class RidgeRanker:
    """Deterministic L2-regularized linear model for cross-sectional ranking."""

    def __init__(self, alpha: float = 1.0, weights: Sequence[float] | None = None) -> None:
        self.alpha = float(alpha)
        self.weights = tuple(weights) if weights is not None else None

    @classmethod
    def fit(
        cls,
        X: Sequence[Sequence[float]],
        y: Sequence[float],
        alpha: float = 1.0,
    ) -> RidgeRanker:
        if not X or not y or len(X) != len(y):
            raise ValueError("X and y must be non-empty with equal sample lengths")

        n_samples = len(X)
        n_features = len(X[0])

        # Compute X^T X
        xtx: list[list[float]] = [[0.0] * n_features for _ in range(n_features)]
        for i in range(n_features):
            for j in range(n_features):
                s = sum(X[k][i] * X[k][j] for k in range(n_samples))
                if i == j:
                    s += float(alpha)  # L2 regularization
                xtx[i][j] = s

        # Compute X^T y
        xty: list[float] = [0.0] * n_features
        for i in range(n_features):
            xty[i] = sum(X[k][i] * y[k] for k in range(n_samples))

        weights = _solve_linear_system(xtx, xty)
        return cls(alpha=alpha, weights=tuple(weights))

    def predict(self, X: Sequence[Sequence[float]]) -> list[float]:
        if self.weights is None:
            raise RuntimeError("Model must be fitted before predicting")

        preds: list[float] = []
        for row in X:
            pred = sum(row[j] * self.weights[j] for j in range(len(row)))
            preds.append(pred)
        return preds
