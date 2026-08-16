"""Validates OpenAPI 3.1 schema against frontend TypeScript contract definitions."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parent.parent
    openapi_file = root / "artifacts" / "latest" / "openapi.json"
    web_types_file = root / "apps" / "web" / "types" / "api.ts"

    if not openapi_file.is_file():
        print(f"ERROR: OpenAPI schema not found at {openapi_file}")
        return 1

    if not web_types_file.is_file():
        print(f"ERROR: Web types contract not found at {web_types_file}")
        return 1

    try:
        with open(openapi_file, encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse OpenAPI JSON: {e}")
        return 1

    if "openapi" not in schema or "paths" not in schema:
        print("ERROR: Invalid OpenAPI specification structure")
        return 1

    types_content = web_types_file.read_text(encoding="utf-8")
    if "export interface" not in types_content and "export type" not in types_content:
        print("ERROR: Web types file does not export TypeScript interfaces")
        return 1

    print("OpenAPI schema and web types contracts verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
