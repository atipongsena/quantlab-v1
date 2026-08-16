from __future__ import annotations

import json
import sys
from pathlib import Path

from quantlab.application.fixtures import verify_fixture


def main() -> int:
    args = sys.argv[1:]
    target = args[0] if args else "data/fixtures/synthetic_v1"
    report = verify_fixture(Path(target))
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
