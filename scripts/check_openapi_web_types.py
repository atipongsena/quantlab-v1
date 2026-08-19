"""Keep the dashboard's typed client in step with the API it reads.

Exports the live FastAPI schema to ``artifacts/latest/openapi.json`` and fails if the
API exposes a path the web client has no reader for. Without this the two drift: the
API grows an endpoint, the dashboard silently never shows it, and nothing is red.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from apps.api.app import app
    except ModuleNotFoundError as err:
        print(
            f"ERROR: cannot import the API ({err}). Install the API extra with "
            f'`pip install -e ".[api]"`.',
            file=sys.stderr,
        )
        return 1

    spec = app.openapi()
    out_path = REPO_ROOT / "artifacts" / "latest" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote OpenAPI {spec['openapi']} schema to {out_path.relative_to(REPO_ROOT)}")

    client_path = REPO_ROOT / "apps" / "web" / "lib" / "api.ts"
    types_path = REPO_ROOT / "apps" / "web" / "types" / "api.ts"
    for path in (client_path, types_path):
        if not path.is_file():
            print(f"ERROR: missing web contract file {path}", file=sys.stderr)
            return 1

    client = client_path.read_text(encoding="utf-8")
    covered = set(re.findall(r'read<[^>]+>\("([^"]+)"\)', client))
    declared = set(spec.get("paths", {}))

    uncovered = sorted(declared - covered)
    unknown = sorted(covered - declared)

    if uncovered:
        print(
            f"ERROR: {len(uncovered)} API path(s) have no reader in apps/web/lib/api.ts:",
            file=sys.stderr,
        )
        for path_name in uncovered:
            print(f"  - {path_name}", file=sys.stderr)
        return 1

    if unknown:
        print(
            f"ERROR: the web client reads {len(unknown)} path(s) the API does not serve:",
            file=sys.stderr,
        )
        for path_name in unknown:
            print(f"  - {path_name}", file=sys.stderr)
        return 1

    exported_types = len(re.findall(r"export interface ", types_path.read_text(encoding="utf-8")))
    print(
        f"All {len(declared)} API paths have a typed reader; "
        f"{exported_types} response interfaces exported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
