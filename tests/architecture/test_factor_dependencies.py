"""Architecture tests verifying quantlab.factors import boundaries."""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTORS_ROOT = PROJECT_ROOT / "quantlab" / "factors"

FORBIDDEN_ROOTS = {
    "quantlab.ml",
    "quantlab.web",
    "quantlab.agent",
    "apps.web",
    "fastapi",
    "pydantic",
    "sklearn",
    "lightgbm",
    "torch",
}


def test_factors_have_no_forbidden_dependencies() -> None:
    violations: list[str] = []

    for path in FACTORS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in FORBIDDEN_ROOTS:
                        if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                            violations.append(
                                f"{path.relative_to(PROJECT_ROOT)} imports forbidden {alias.name}"
                            )
            elif isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in FORBIDDEN_ROOTS:
                    if node.module == forbidden or node.module.startswith(f"{forbidden}."):
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)} imports forbidden {node.module}"
                        )

    assert not violations, "\n".join(violations)
