"""Tests for train-only preprocessing."""

from quantlab.ml.preprocessing import TrainOnlyPreprocessor


def test_train_only_preprocessor_standardization() -> None:
    X_train = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0], [5.0, 50.0]]
    prep = TrainOnlyPreprocessor.fit(X_train)

    assert prep.is_fitted

    # Transform on test data uses train parameters
    X_test = [[3.0, 30.0]]
    X_test_trans = prep.transform(X_test)

    # 3.0 is exact mean of train, so standardized value should be near 0.0
    assert abs(X_test_trans[0][0]) < 1e-4
    assert abs(X_test_trans[0][1]) < 1e-4
