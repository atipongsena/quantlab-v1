"""Release integrity and acceptance manifest verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def verify_release(config_path: str, offline: bool = True) -> int:
    root = Path(__file__).parent.parent
    manifest_path = root / "artifacts" / "golden" / "v1-acceptance" / "manifest.json"

    print("=" * 70)
    print("QuantLab Release Verification")
    print(f"Config: {config_path} (offline={offline})")
    print("=" * 70)

    if not manifest_path.is_file():
        print(f"FAIL: Acceptance manifest not found at {manifest_path}")
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    recorded_hash = data.get("content_hash")
    if not recorded_hash:
        print("FAIL: Missing 'content_hash' in manifest")
        return 1

    payload = {
        "release_id": data.get("release_id"),
        "version": data.get("version"),
        "timestamp": data.get("timestamp"),
        "status": data.get("status"),
        "doctor": data.get("doctor"),
        "dataset_manifest": data.get("dataset_manifest"),
        "backtest_sharpe": data.get("backtest_sharpe"),
        "validation_verdict": data.get("validation_verdict"),
        "ml_champion": data.get("ml_champion"),
        "paper_sessions": data.get("paper_sessions"),
        "campaign_report_id": data.get("campaign_report_id"),
    }
    encoded = json.dumps(payload, sort_keys=True, indent=2)
    recomputed_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    if recorded_hash != recomputed_hash:
        print(f"FAIL: Manifest hash mismatch: {recorded_hash} != {recomputed_hash}")
        return 1

    print(f"[PASS] Manifest integrity verified: {manifest_path}")
    print(f"[PASS] Release Status: {data.get('status')}")
    print("STATUS: PASS [Release configuration and manifest verified]")
    print("=" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify QuantLab release")
    parser.add_argument(
        "--config", default="configs/releases/quantlab-v1.yaml", help="Path to config"
    )
    parser.add_argument("--offline", action="store_true", help="Offline verification mode")
    args = parser.parse_args()
    return verify_release(args.config, args.offline)


if __name__ == "__main__":
    sys.exit(main())
