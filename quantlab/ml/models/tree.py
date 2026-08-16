"""Deterministic gradient boosted decision tree ranker."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TreeNode:
    feature_index: int = -1
    threshold: float = 0.0
    left_value: float | None = None
    right_value: float | None = None
    left_node: TreeNode | None = None
    right_node: TreeNode | None = None
    is_leaf: bool = False
    leaf_value: float = 0.0


class SimpleDecisionTree:
    """Single decision tree regressor."""

    def __init__(self, max_depth: int = 3, min_samples_split: int = 5) -> None:
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.root: TreeNode | None = None

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[float]) -> SimpleDecisionTree:
        self.root = self._build_tree(X, y, depth=0)
        return self

    def _build_tree(self, X: Sequence[Sequence[float]], y: Sequence[float], depth: int) -> TreeNode:
        n_samples = len(y)
        if n_samples == 0:
            return TreeNode(is_leaf=True, leaf_value=0.0)

        mean_y = sum(y) / n_samples
        if depth >= self.max_depth or n_samples < self.min_samples_split:
            return TreeNode(is_leaf=True, leaf_value=mean_y)

        n_features = len(X[0])
        best_feat = -1
        best_thresh = 0.0
        best_var_reduction = -1.0
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        for j in range(n_features):
            # Sort sample indices by feature j
            sorted_indices = sorted(range(n_samples), key=lambda i: X[i][j])
            sum_left = 0.0
            total_sum = sum(y)

            for k in range(n_samples - 1):
                idx = sorted_indices[k]
                sum_left += y[idx]
                next_idx = sorted_indices[k + 1]

                if X[idx][j] == X[next_idx][j]:
                    continue

                count_left = k + 1
                count_right = n_samples - count_left
                sum_right = total_sum - sum_left

                var_red = (
                    (sum_left**2 / count_left)
                    + (sum_right**2 / count_right)
                    - (total_sum**2 / n_samples)
                )
                if var_red > best_var_reduction:
                    best_var_reduction = var_red
                    best_feat = j
                    best_thresh = (X[idx][j] + X[next_idx][j]) / 2.0
                    best_left_idx = sorted_indices[:count_left]
                    best_right_idx = sorted_indices[count_left:]

        if best_feat == -1:
            return TreeNode(is_leaf=True, leaf_value=mean_y)

        left_X = [X[i] for i in best_left_idx]
        left_y_sub = [y[i] for i in best_left_idx]
        right_X = [X[i] for i in best_right_idx]
        right_y_sub = [y[i] for i in best_right_idx]

        left_child = self._build_tree(left_X, left_y_sub, depth + 1)
        right_child = self._build_tree(right_X, right_y_sub, depth + 1)

        return TreeNode(
            feature_index=best_feat,
            threshold=best_thresh,
            left_node=left_child,
            right_node=right_child,
            is_leaf=False,
        )

    def predict_row(self, row: Sequence[float], node: TreeNode | None = None) -> float:
        cur = node or self.root
        if cur is None or cur.is_leaf:
            return cur.leaf_value if cur is not None else 0.0

        if row[cur.feature_index] <= cur.threshold:
            return self.predict_row(row, cur.left_node)
        return self.predict_row(row, cur.right_node)


class LightGBMRanker:
    """Gradient boosted decision tree ranker implementing LightGBM-style learning."""

    def __init__(
        self,
        n_estimators: int = 50,
        learning_rate: float = 0.05,
        max_depth: int = 3,
        trees: Sequence[SimpleDecisionTree] | None = None,
        base_pred: float = 0.0,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.trees = tuple(trees) if trees is not None else None
        self.base_pred = base_pred

    @classmethod
    def fit(
        cls,
        X: Sequence[Sequence[float]],
        y: Sequence[float],
        n_estimators: int = 30,
        learning_rate: float = 0.05,
        max_depth: int = 3,
    ) -> LightGBMRanker:
        if not X or not y:
            raise ValueError("X and y must not be empty")

        n_samples = len(y)
        base_pred = sum(y) / n_samples
        current_preds = [base_pred] * n_samples

        fitted_trees: list[SimpleDecisionTree] = []

        for _ in range(n_estimators):
            # Compute negative gradient (residuals for MSE loss)
            residuals = [y[i] - current_preds[i] for i in range(n_samples)]

            tree = SimpleDecisionTree(max_depth=max_depth)
            tree.fit(X, residuals)
            fitted_trees.append(tree)

            # Update predictions
            for i in range(n_samples):
                current_preds[i] += learning_rate * tree.predict_row(X[i])

        return cls(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            trees=fitted_trees,
            base_pred=base_pred,
        )

    def predict(self, X: Sequence[Sequence[float]]) -> list[float]:
        if self.trees is None:
            raise RuntimeError("Model must be fitted before predicting")

        preds: list[float] = []
        for row in X:
            val = self.base_pred
            for tree in self.trees:
                val += self.learning_rate * tree.predict_row(row)
            preds.append(val)
        return preds
