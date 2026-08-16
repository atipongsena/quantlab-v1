"""End-to-end CLI tests for quantlab model compare."""

from apps.cli.main import app


def test_model_compare_cli_json(capsys) -> None:
    code = app(
        [
            "model",
            "compare",
            "--dataset",
            "DATASET-v001",
            "--walk-forward",
            "configs/ml/walk-forward-v1.yaml",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "champion_model" in captured.out
    assert "reports" in captured.out


def test_model_compare_cli_text(capsys) -> None:
    code = app(
        [
            "model",
            "compare",
            "--dataset",
            "DATASET-v001",
            "--walk-forward",
            "configs/ml/walk-forward-v1.yaml",
            "--output",
            "text",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "QuantLab Walk-Forward Cross-Validation" in captured.out
    assert "Champion Model" in captured.out
