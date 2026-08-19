"""End-to-end tests for the dataset build and inspect commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.cli.main import app


def test_dataset_cli_build_and_inspect_e2e(in_synthetic_workspace: Path) -> None:
    build_exit = app(["dataset", "build", "configs/datasets/synthetic-v001.yaml", "--offline"])
    assert build_exit == 0

    # --verify-hash recomputes the partition hashes and compares them against the
    # manifest, so this fails if a published dataset was altered after the fact.
    inspect_exit = app(["dataset", "inspect", "DATASET-v001", "--verify-hash"])
    assert inspect_exit == 0

    assert (in_synthetic_workspace / "artifacts/datasets/DATASET-v001/manifest.json").is_file()


def test_inspecting_an_unbuilt_dataset_is_not_reported_as_healthy(
    in_synthetic_workspace: Path,
) -> None:
    """A dataset that was never built must raise, not report a clean manifest."""
    with pytest.raises(FileNotFoundError):
        app(["dataset", "inspect", "DATASET-NEVER-BUILT", "--verify-hash"])
