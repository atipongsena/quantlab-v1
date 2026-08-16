"""End-to-end tests for paper trading CLI commands."""

from apps.cli.main import app


def test_paper_run_cli_json(capsys) -> None:
    code = app(
        [
            "paper",
            "run",
            "--date",
            "2026-01-05",
            "--strategy",
            "configs/strategies/composite-top30-v1.yaml",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "COMPLETED" in captured.out
    assert "orders_count" in captured.out


def test_paper_reconcile_cli_json(capsys) -> None:
    code = app(
        [
            "paper",
            "reconcile",
            "--date",
            "2026-01-05",
            "--strategy",
            "configs/strategies/composite-top30-v1.yaml",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "is_clean" in captured.out
    assert "content_hash" in captured.out


def test_paper_run_cli_text(capsys) -> None:
    code = app(
        [
            "paper",
            "run",
            "--date",
            "2026-01-05",
            "--strategy",
            "configs/strategies/composite-top30-v1.yaml",
            "--output",
            "text",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "QuantLab Paper Trading Daily Operational Cycle" in captured.out
    assert "Status: PASS" in captured.out


def test_paper_reconcile_cli_text(capsys) -> None:
    code = app(
        [
            "paper",
            "reconcile",
            "--date",
            "2026-01-05",
            "--strategy",
            "configs/strategies/composite-top30-v1.yaml",
            "--output",
            "text",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "QuantLab Shadow Position & Cash Reconciliation" in captured.out
    assert "Status: PASS" in captured.out
