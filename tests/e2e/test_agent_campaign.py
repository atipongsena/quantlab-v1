"""End-to-end tests for autonomous agent research campaigns and report verifier CLI."""

from pathlib import Path

from apps.cli.main import app


def test_agent_campaign_and_report_verify_cli(capsys, tmp_path: Path) -> None:
    # 1. Run campaign
    code = app(
        [
            "campaign",
            "run",
            "configs/campaigns/quality-improves-momentum-v1.yaml",
            "--llm",
            "fake",
            "--offline",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "quality-improves-momentum-v1" in captured.out
    assert "HYP-001" in captured.out
    assert "VALIDATED" in captured.out

    # 2. Verify report
    report_file = Path("artifacts/latest/research-report.json")
    assert report_file.is_file()

    verify_code = app(
        [
            "report",
            "verify",
            str(report_file),
        ]
    )
    assert verify_code == 0
    verify_captured = capsys.readouterr()
    assert "VERIFIED [PASS]" in verify_captured.out
