"""Tests for MLEvaluationEngine metrics."""

from quantlab.ml.evaluation import MLEvaluationEngine


def test_ml_evaluation_spearman_ic_and_report() -> None:
    preds = [1.0, 2.0, 3.0, 4.0, 5.0]
    targets = [10.0, 20.0, 30.0, 40.0, 50.0]

    ic = MLEvaluationEngine.compute_spearman_ic(preds, targets)
    assert abs(ic - 1.0) < 1e-4

    report = MLEvaluationEngine.evaluate_model("test_model", [(preds, targets)])
    assert report.model_name == "test_model"
    assert report.mean_ic > 0.9
    assert report.is_monotonic
