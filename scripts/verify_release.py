"""Verify the acceptance record has not been edited since it was produced.

The record is signed over every field it contains except the signature itself. The
previous version listed the fields to hash by hand, so any field the acceptance runner
started emitting was left out of the signature and could be changed afterwards without
detection - and the moment the runner's output shape changed, verification failed for a
reason that had nothing to do with tampering.

    python scripts/verify_release.py --config configs/releases/quantlab-v1.yaml --offline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SIGNATURE_FIELD = "content_hash"

# Fields the record must carry for the verification to mean anything. A record missing
# the verdict or the dataset hash would still verify as untampered while saying nothing.
REQUIRED_FIELDS = (
    "release_id",
    "dataset_id",
    "dataset_manifest_hash",
    "backtest_content_hash",
    "validation_verdict",
    "ml_champion",
)


def sign(record: dict[str, Any]) -> str:
    """Hash every field except the signature, in a canonical ordering."""
    payload = {key: value for key, value in record.items() if key != SIGNATURE_FIELD}
    encoded = json.dumps(payload, sort_keys=True, indent=2)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def verify_release(config_path: str, manifest_path: Path, offline: bool = True) -> int:
    print("=" * 70)
    print("QuantLab release verification")
    print(f"Config: {config_path} (offline={offline})")
    print("=" * 70)

    if not manifest_path.is_file():
        print(
            f"FAIL: no acceptance record at {manifest_path}. "
            f"Produce one with: python scripts/run_v1_acceptance.py",
            file=sys.stderr,
        )
        return 1

    with open(manifest_path, encoding="utf-8") as handle:
        record = json.load(handle)

    recorded = record.get(SIGNATURE_FIELD)
    if not recorded:
        print(f"FAIL: record carries no '{SIGNATURE_FIELD}'", file=sys.stderr)
        return 1

    missing = [field for field in REQUIRED_FIELDS if record.get(field) in (None, "")]
    if missing:
        print(f"FAIL: record is missing required fields: {', '.join(missing)}", file=sys.stderr)
        return 1

    recomputed = sign(record)
    if recorded != recomputed:
        print(
            f"FAIL: the record has been edited since it was signed.\n"
            f"  recorded   {recorded}\n"
            f"  recomputed {recomputed}",
            file=sys.stderr,
        )
        return 1

    print(f"  ok  signature verified over {len(record) - 1} fields")
    print(f"  ok  release        : {record['release_id']} v{record.get('version', '?')}")
    print(f"  ok  dataset        : {record['dataset_id']} ({record['dataset_manifest_hash'][:16]})")
    print(f"  ok  backtest       : {record['backtest_content_hash'][:16]}")
    print(f"  ok  verdict        : {record['validation_verdict']}")
    print(f"  ok  champion model : {record['ml_champion']}")
    print("=" * 70)
    print("PASS: acceptance record is intact")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/releases/quantlab-v1.yaml")
    parser.add_argument(
        "--manifest",
        default="artifacts/golden/v1-acceptance/manifest.json",
        help="Path to the acceptance record to verify",
    )
    parser.add_argument("--offline", action="store_true", help="Offline verification mode")
    args = parser.parse_args(argv)
    return verify_release(args.config, REPO_ROOT / args.manifest, args.offline)


if __name__ == "__main__":
    raise SystemExit(main())
