"""Behavioral checks for the milestone scope guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCOPE_CHECK = PROJECT_ROOT / "scripts" / "check_scope.py"


def run_scope_check(root: Path, milestone: str) -> tuple[int, dict[str, object]]:
    """Run the real guard against an isolated filesystem tree."""
    completed = subprocess.run(
        [sys.executable, str(SCOPE_CHECK), milestone],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_scope_rejects_premature_packages(tmp_path: Path) -> None:
    """Adding a package assigned to a future milestone must halt M0 work."""
    (tmp_path / "quantlab" / "data").mkdir(parents=True)
    (tmp_path / "quantlab" / "data" / "__init__.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M1",
                "kind": "premature_package",
                "path": "quantlab/data",
            }
        ],
    }


def test_scope_rejects_premature_namespace_packages(tmp_path: Path) -> None:
    """Removing directory checks would allow an uninitialized M8 web package in M0."""
    (tmp_path / "apps" / "web").mkdir(parents=True)

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M8",
                "kind": "premature_package",
                "path": "apps/web",
            }
        ],
    }


def test_scope_allows_m0_package_roots(tmp_path: Path) -> None:
    """The package boundaries explicitly introduced in M0 are accepted."""
    (tmp_path / "quantlab").mkdir()
    (tmp_path / "quantlab" / "__init__.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 0
    assert result == {"milestone": "M0", "status": "ok", "violations": []}


def test_scope_rejects_forbidden_content_in_neutral_source_and_config_files(
    tmp_path: Path,
) -> None:
    """Removing content checks would allow forbidden capabilities behind neutral paths."""
    source_file = tmp_path / "quantlab" / "runner.py"
    source_file.parent.mkdir()
    source_file.write_text(
        'execution_frequency = "intraday"\norder_destination = "live-money"\n',
        encoding="utf-8",
    )
    config_file = tmp_path / "configs" / "runtime.toml"
    config_file.parent.mkdir()
    config_file.write_text(
        'instrument_class = "options"\nderivative_kind = "derivatives"\nexposure = "leveraged"\n',
        encoding="utf-8",
    )

    exit_code, result = run_scope_check(tmp_path, "M9")

    assert exit_code == 2
    assert result == {
        "milestone": "M9",
        "status": "rejected",
        "violations": [
            {
                "kind": "forbidden_v1_feature",
                "path": "quantlab/runner.py",
                "rule": "live_money",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "quantlab/runner.py",
                "rule": "intraday",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "options",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "derivatives",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "leverage",
            },
        ],
    }


def test_scope_rejects_premature_dependencies_in_metadata(tmp_path: Path) -> None:
    """Removing metadata checks would allow M5 and M8 dependencies during M0."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi==0.1.0"]\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements.lock").write_text("lightgbm==4.0.0\n", encoding="utf-8")

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M8",
                "dependency": "fastapi",
                "kind": "premature_dependency",
                "path": "pyproject.toml",
            },
            {
                "available_in": "M5",
                "dependency": "lightgbm",
                "kind": "premature_dependency",
                "path": "requirements.lock",
            },
        ],
    }


def test_scope_rejects_forbidden_v1_features(tmp_path: Path) -> None:
    """V1 non-goals must be rejected even after their nominal milestone."""
    forbidden_markers = (
        "live_money",
        "intraday",
        "tick_data",
        "high_frequency",
        "options",
        "futures",
        "forex",
        "crypto",
        "shorting",
        "leverage",
        "borrow_model",
        "reinforcement_learning",
        "lstm",
        "transformer",
        "alternative_data",
        "paid_data",
        "factor_library",
        "arbitrary_strategy_code",
        "agent_swarm",
        "kubernetes",
        "spark",
        "multi_tenancy",
        "tax_accounting",
    )
    source_root = tmp_path / "quantlab"
    source_root.mkdir()
    for marker in forbidden_markers:
        (source_root / f"{marker}.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M9")

    assert exit_code == 2
    assert result["milestone"] == "M9"
    assert result["status"] == "rejected"
    assert result["violations"] == [
        {
            "kind": "forbidden_v1_feature",
            "path": f"quantlab/{marker}.py",
            "rule": marker,
        }
        for marker in forbidden_markers
    ]
