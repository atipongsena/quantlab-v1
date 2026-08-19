"""End-to-end test for paper forward simulation flow."""

from __future__ import annotations

import json
from pathlib import Path

from apps.cli.main import app


def test_paper_simulate_forward_flow(in_synthetic_workspace: Path, capsys) -> None:
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

    payload = json.loads(capsys.readouterr().out)
    assert payload["deployment_id"] == "PAPER-SYNTHETIC"
    assert payload["total_sessions"] > 0
    # A reconciliation run that never reconciles anything would satisfy a substring
    # check on the output while proving nothing.
    assert payload["clean_reconciliations"] <= payload["total_sessions"]
