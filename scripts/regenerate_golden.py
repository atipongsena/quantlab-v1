"""Regenerate the golden backtest record.

Run this only after reviewing why the golden regression test failed. A golden record
that gets refreshed reflexively records whatever the code does today and stops being
evidence of anything.

    python scripts/regenerate_golden.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.backtest.test_golden_backtest import (  # noqa: E402
    GOLDEN_PATH,
    _prepare_workspace,
    _run,
    _summary,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        workspace = _prepare_workspace(Path(tmp))
        summary = _summary(_run(workspace))

    previous = None
    if GOLDEN_PATH.exists():
        previous = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if previous is None:
        print(f"Created golden record at {GOLDEN_PATH}")
    else:
        changed = {k: (previous.get(k), v) for k, v in summary.items() if previous.get(k) != v}
        if not changed:
            print("Golden record unchanged.")
        else:
            print(f"Golden record updated at {GOLDEN_PATH}. Changed fields:")
            for key, (was, now) in changed.items():
                print(f"  {key}: {was} -> {now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
