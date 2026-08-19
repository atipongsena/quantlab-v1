"""End-to-end tests for paper trading CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from apps.cli.main import app

STRATEGY = "configs/strategies/composite-top30-v1.yaml"


def test_paper_run_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    code = app(["paper", "run", "--date", "2026-01-05", "--strategy", STRATEGY, "--output", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "COMPLETED"
    assert payload["orders_count"] >= 0


def test_paper_reconcile_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        ["paper", "reconcile", "--date", "2026-01-05", "--strategy", STRATEGY, "--output", "json"]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    # A reconciliation is only meaningful if it reports a signed drift and a content
    # hash; "is_clean" alone could be a constant.
    assert isinstance(payload["is_clean"], bool)
    assert len(payload["content_hash"]) == 64


def test_paper_run_cli_text(in_synthetic_workspace: Path, capsys) -> None:
    code = app(["paper", "run", "--date", "2026-01-05", "--strategy", STRATEGY, "--output", "text"])
    assert code == 0
    out = capsys.readouterr().out
    assert "QuantLab Paper Trading Daily Operational Cycle" in out
    assert "Status: PASS" in out


def test_paper_reconcile_cli_text(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        ["paper", "reconcile", "--date", "2026-01-05", "--strategy", STRATEGY, "--output", "text"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "QuantLab Shadow Position & Cash Reconciliation" in out
    assert "Status: PASS" in out
