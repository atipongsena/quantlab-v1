"""Tests for RidgeRanker model."""

from quantlab.ml.models.linear import RidgeRanker


def test_ridge_ranker_learns_positive_slope() -> None:
    # Perfect linear relation: y = 2.0 * x1 + 0.5 * x2
    X = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0], [5.0, 10.0]]
    y = [3.0, 6.0, 9.0, 12.0, 15.0]

    model = RidgeRanker.fit(X, y, alpha=0.01)
    preds = model.predict([[6.0, 12.0]])

    assert len(preds) == 1
    assert abs(preds[0] - 18.0) < 0.2
