"""End-to-end test for paper forward simulation flow."""

from apps.cli.main import app


def test_paper_simulate_forward_flow(capsys) -> None:
    code = app(
        [
            "paper",
            "simulate",
            "--deployment",
            "PAPER-SYNTHETIC",
            "--sessions",
            "2024-01-01:2024-04-30",
            "--clock",
            "fixture",
            "--offline",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "PAPER-SYNTHETIC" in captured.out
    assert "clean_reconciliations" in captured.out
    assert "total_sessions" in captured.out
