from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = PROJECT_ROOT / "quantlab" / "domain"

FORBIDDEN_IMPORT_ROOTS = {
    "apps",
    "fastapi",
    "llm",
    "mcp",
    "pydantic",
    "sqlalchemy",
    "ui",
}
FORBIDDEN_QUANTLAB_LAYERS = {
    "application",
    "data",
    "infrastructure",
    "providers",
    "web",
}


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            parts = node.module.split(".")
            if parts[0] == "quantlab" and len(parts) > 1:
                roots.add("quantlab." + parts[1])
            else:
                roots.add(parts[0])
    return roots


def test_domain_has_no_forbidden_imports() -> None:
    violations: list[str] = []
    stdlib_roots = sys.stdlib_module_names | {"__future__"}

    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for root in sorted(_import_roots(tree)):
            if root in stdlib_roots:
                continue
            if root == "quantlab.domain":
                continue
            if root in FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports forbidden {root}")
                continue
            if root.startswith("quantlab."):
                layer = root.split(".", 1)[1]
                if layer in FORBIDDEN_QUANTLAB_LAYERS:
                    violations.append(f"{path.relative_to(PROJECT_ROOT)} imports forbidden {root}")
                    continue
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)} imports non-domain dependency {root}"
            )

    assert violations == []
