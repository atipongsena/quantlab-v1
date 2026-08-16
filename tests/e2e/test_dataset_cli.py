from __future__ import annotations

from pathlib import Path

from apps.cli.main import app


def test_dataset_cli_build_and_inspect_e2e(tmp_path: Path) -> None:
    # 1. Build synthetic dataset
    config_path = "configs/datasets/synthetic-v001.yaml"
    build_exit = app(["dataset", "build", config_path, "--offline"])
    assert build_exit == 0

    # 2. Inspect dataset with hash verification
    inspect_exit = app(["dataset", "inspect", "DATASET-v001", "--verify-hash"])
    assert inspect_exit == 0

    # 3. Verify manifest file exists in artifacts
    manifest_path = Path("artifacts/datasets/DATASET-v001/manifest.json")
    assert manifest_path.exists()
