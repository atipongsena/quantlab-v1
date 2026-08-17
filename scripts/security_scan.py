"""Security and vulnerability scanner for QuantLab codebase."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SUSPICIOUS_PATTERNS = (
    (
        "hardcoded_secret",
        re.compile(
            r"""(?:api[_-]?key|secret[_-]?key|password)\s*=\s*"""
            r"""['"][a-zA-Z0-9_\-]{20,}['"]""",
            re.IGNORECASE,
        ),
    ),
    ("unsafe_eval", re.compile(r"""\beval\s*\(\s*(?:request|input|sys\.stdin)""")),
)


def run_security_scan() -> int:
    root = Path(__file__).parent.parent
    findings: list[tuple[str, str, int]] = []

    for path in root.rglob("*.py"):
        if ".venv" in path.parts or ".superpowers" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for rule_name, pattern in SUSPICIOUS_PATTERNS:
                if pattern.search(line):
                    findings.append((rule_name, str(path.relative_to(root)), line_num))

    print("=" * 70)
    print("QuantLab Security & Vulnerability Scan")
    print("=" * 70)
    if findings:
        for rule, p, line_num in findings:
            print(f"SECURITY ISSUE [{rule}]: {p}:{line_num}")
        print("=" * 70)
        return 1

    print("No security vulnerabilities or secret leaks detected.")
    print("STATUS: PASS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_security_scan())
