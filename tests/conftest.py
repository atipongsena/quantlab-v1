"""Project-wide pytest configuration."""

from __future__ import annotations

import shutil
from collections.abc import Generator
from pathlib import Path

import pytest

pytest_plugins = ("tests.socket_guard",)

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def synthetic_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway working directory with the synthetic dataset already built.

    End-to-end tests used to run against whatever database happened to be sitting in the
    repository, so they passed on a developer machine that had run `dataset build` and
    failed on a clean clone. Building into a temporary directory makes the suite say the
    same thing everywhere.
    """
    workspace = tmp_path_factory.mktemp("workspace")
    for relative in ("configs", "migrations", "data/fixtures/synthetic_v1"):
        source = REPO_ROOT / relative
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)

    from quantlab.application.dataset_service import DatasetService

    DatasetService(base_dir=workspace).build_dataset("configs/datasets/synthetic-v001.yaml")
    return workspace


@pytest.fixture
def in_synthetic_workspace(
    synthetic_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """Run a test with the process working directory inside the built workspace."""
    monkeypatch.chdir(synthetic_workspace)
    yield synthetic_workspace


@pytest.fixture(scope="session", autouse=True)
def artifacts_are_not_touched_by_tests() -> Generator[None, None, None]:
    """Fail if a test writes into the repository's evidence artifacts.

    There used to be a fixture here that snapshotted those files and restored them
    afterwards. That hid the leak rather than fixing it, and it silently reverted
    artifacts a real run had just produced. Tests build into temporary workspaces now
    (see ``synthetic_workspace``), so any write to these paths is a bug in the test.
    """
    root = Path(__file__).parent.parent
    watched = sorted((root / "artifacts" / "latest").rglob("*.json")) + [
        root / "artifacts/datasets/DATASET-v001/manifest.json"
    ]
    before = {path: path.read_bytes() for path in watched if path.is_file()}

    yield

    modified = [
        str(path.relative_to(root))
        for path, content in before.items()
        if path.is_file() and path.read_bytes() != content
    ]
    if modified:
        pytest.fail(
            "Tests wrote into the repository's evidence artifacts: "
            + ", ".join(modified)
            + ". Build into a temporary workspace instead."
        )
