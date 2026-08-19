"""End-to-end tests for autonomous agent research campaigns and the report verifier."""

from __future__ import annotations

from pathlib import Path

from apps.cli.main import app


def test_agent_campaign_and_report_verify_cli(in_synthetic_workspace: Path, capsys) -> None:
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
    out = capsys.readouterr().out
    assert "quality-improves-momentum-v1" in out
    assert "HYP-001" in out
    assert "VALIDATED" in out

    report_file = in_synthetic_workspace / "artifacts/latest/research-report.json"
    assert report_file.is_file()

    assert app(["report", "verify", str(report_file)]) == 0
    assert "VERIFIED [PASS]" in capsys.readouterr().out


def test_report_verify_rejects_a_tampered_report(in_synthetic_workspace: Path, capsys) -> None:
    """The signature has to actually detect edits, or it is decoration.

    A research report whose numbers can be changed after signing is not evidence of
    anything.
    """
    assert (
        app(
            [
                "campaign",
                "run",
                "configs/campaigns/quality-improves-momentum-v1.yaml",
                "--llm",
                "fake",
                "--offline",
            ]
        )
        == 0
    )
    capsys.readouterr()

    report_file = in_synthetic_workspace / "artifacts/latest/research-report.json"
    tampered = report_file.read_text(encoding="utf-8").replace("VALIDATED", "REJECTED", 1)
    report_file.write_text(tampered, encoding="utf-8")

    assert app(["report", "verify", str(report_file)]) != 0
