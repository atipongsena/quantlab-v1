"""Tests for gradient boosted decision tree ranker."""

from quantlab.ml.models.tree import LightGBMRanker


def test_lightgbm_ranker_fits_nonlinear_pattern() -> None:
    # X in [0..10], y = 1 if x > 5 else -1
    X = [[float(i)] for i in range(11)]
    y = [1.0 if i > 5 else -1.0 for i in range(11)]

    model = LightGBMRanker.fit(X, y, n_estimators=10, learning_rate=0.2, max_depth=2)
    preds = model.predict([[2.0], [8.0]])

    assert len(preds) == 2
    assert preds[0] < preds[1]  # Higher score for higher x
