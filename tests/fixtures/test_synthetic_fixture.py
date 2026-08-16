from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from quantlab.application.fixtures import verify_fixture


def test_fixture_contains_required_temporal_canaries() -> None:
    fixture_dir = Path("data/fixtures/synthetic_v1")
    report = verify_fixture(fixture_dir)
    assert report.status == "PASS"

    source_dir = fixture_dir / "source"

    # 1. Listings check: AAPL, MSFT, FB/META rename, delisted instrument, ETF
    with open(source_dir / "listings.csv", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        symbols = {r["symbol"] for r in reader}
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "FB" in symbols
        assert "META" in symbols
        assert "DELIST_CORP" in symbols
        assert "SPY" in symbols

    # 2. Corporate actions check: split, dividend, rename, delisting
    with open(source_dir / "actions.csv", encoding="utf-8") as f:
        actions = list(csv.DictReader(f))
        action_types = {a["action_type"] for a in actions}
        assert "SPLIT" in action_types
        assert "DIVIDEND" in action_types
        assert "SYMBOL_CHANGE" in action_types
        assert "DELISTING" in action_types

    # 3. Fundamentals check: 2020-03-01 canary filing & restatement
    with open(source_dir / "fundamentals.csv", encoding="utf-8") as f:
        funds = list(csv.DictReader(f))
        canaries = [f for f in funds if f["symbol"] == "AAPL" and f["period_end"] == "2019-12-31"]
        assert len(canaries) == 2
        availabilities = {c["available_at"] for c in canaries}
        assert "2020-02-20T21:00:00Z" in availabilities
        assert "2020-04-15T21:00:00Z" in availabilities

    # 4. Prices check: missing open canary on 2021-06-15 & >= 36 monthly decision dates
    with open(source_dir / "prices.csv", encoding="utf-8") as f:
        prices = list(csv.DictReader(f))
        missing_open_row = [
            p for p in prices if p["symbol"] == "AAPL" and p["date"] == "2021-06-15"
        ]
        assert len(missing_open_row) == 1
        assert missing_open_row[0]["open"] == ""

        # Monthly decision dates
        dates = sorted({p["date"] for p in prices if p["symbol"] == "AAPL"})
        months = sorted({datetime.fromisoformat(d).strftime("%Y-%m") for d in dates})
        assert len(months) >= 36


def test_fixture_hash_detects_mutation(tmp_path: Path) -> None:
    # Copy fixture to tmp_path
    fixture_dir = Path("data/fixtures/synthetic_v1")
    target_fixture = tmp_path / "synthetic_v1"
    target_fixture.mkdir(parents=True, exist_ok=True)
    target_source = target_fixture / "source"
    target_source.mkdir(parents=True, exist_ok=True)

    manifest_content = (fixture_dir / "manifest.json").read_text(encoding="utf-8")
    (target_fixture / "manifest.json").write_text(manifest_content, encoding="utf-8")

    for file in (fixture_dir / "source").glob("*.csv"):
        (target_source / file.name).write_bytes(file.read_bytes())

    # Initial verification passes
    report = verify_fixture(target_fixture)
    assert report.status == "PASS"

    # Mutate a file
    (target_source / "prices.csv").write_text("corrupted,prices,data\n", encoding="utf-8")
    mutated_report = verify_fixture(target_fixture)
    assert mutated_report.status == "FAIL"
    assert len(mutated_report.errors) > 0
