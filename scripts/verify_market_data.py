"""Cross-check the engine's corporate-action math against the data provider.

The fixture stores as-traded prices plus a split and dividend history. Yahoo separately
publishes its own total-return series (``Adj Close``) computed from the same events. If
QuantLab's backward adjustment is correct, re-deriving the total-return series from raw
price plus actions must reproduce Yahoo's series to within rounding.

This is the check that makes the rest of the research trustworthy: a factor library can
look statistically healthy while silently running on double-adjusted or unadjusted
prices, and nothing downstream would notice.

Usage:
    python scripts/verify_market_data.py --fixture us_research
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

from quantlab.data.corporate_actions import apply_adjustments
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar

REPO_ROOT = Path(__file__).resolve().parent.parent

# Yahoo rounds its published adjusted close to six figures and applies dividend factors
# at slightly different precision, so an exact match is not achievable. A median relative
# error above this threshold means the adjustment logic itself disagrees, not rounding.
MEDIAN_TOLERANCE = 0.005
WORST_CASE_TOLERANCE = 0.05


def _instrument_id(symbol: str) -> InstrumentId:
    return InstrumentId.from_uuid(uuid5(NAMESPACE_DNS, f"quantlab.entity.{symbol.lower()}"))


def _load_prices(path: Path) -> dict[str, list[MarketBar]]:
    by_symbol: dict[str, list[MarketBar]] = defaultdict(list)
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            symbol = row["symbol"].strip().upper()
            session = date.fromisoformat(row["date"].strip())
            by_symbol[symbol].append(
                MarketBar(
                    instrument_id=_instrument_id(symbol),
                    session=session,
                    observed_at=datetime(
                        session.year, session.month, session.day, 21, 0, tzinfo=UTC
                    ),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=Decimal(row["volume"] or "0"),
                    semantic=BarPriceSemantic.RAW,
                    source="fixture",
                )
            )
    return by_symbol


def _load_actions(path: Path) -> dict[str, list[CorporateAction]]:
    by_symbol: dict[str, list[CorporateAction]] = defaultdict(list)
    if not path.exists():
        return by_symbol
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            symbol = row["symbol"].strip().upper()
            effective = date.fromisoformat(row["effective_date"].strip())
            announced = datetime(effective.year, effective.month, effective.day, 9, 0, tzinfo=UTC)
            ratio = row.get("ratio", "").strip()
            cash = row.get("cash_amount", "").strip()
            by_symbol[symbol].append(
                CorporateAction(
                    instrument_id=_instrument_id(symbol),
                    action_type=CorporateActionType(row["action_type"].strip().lower()),
                    effective_at=effective,
                    announced_at=announced,
                    available_at=announced,
                    ratio=Decimal(ratio) if ratio else None,
                    cash_amount=Decimal(cash) if cash else None,
                    source="fixture",
                )
            )
    return by_symbol


def _load_reference(path: Path) -> dict[str, dict[date, float]]:
    by_symbol: dict[str, dict[date, float]] = defaultdict(dict)
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_symbol[row["symbol"].strip().upper()][date.fromisoformat(row["date"].strip())] = (
                float(row["adj_close"])
            )
    return by_symbol


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def verify(fixture_dir: Path) -> int:
    source = fixture_dir / "source"
    prices_path = source / "prices.csv"
    reference_path = source / "reference_adjusted_close.csv"

    if not prices_path.exists():
        print(f"No prices.csv under {source}", file=sys.stderr)
        return 1
    if not reference_path.exists():
        print(
            f"No reference_adjusted_close.csv under {source}. Re-run "
            f"scripts/download_real_market_data.py to capture the provider series.",
            file=sys.stderr,
        )
        return 1

    print("=" * 78)
    print("Corporate action verification: engine adjustment vs provider Adj Close")
    print("=" * 78)

    bars_by_symbol = _load_prices(prices_path)
    actions_by_symbol = _load_actions(source / "actions.csv")
    reference_by_symbol = _load_reference(reference_path)

    results: list[dict[str, object]] = []
    failures: list[str] = []

    for symbol in sorted(bars_by_symbol):
        bars = sorted(bars_by_symbol[symbol], key=lambda b: b.session)
        actions = actions_by_symbol.get(symbol, [])
        reference = reference_by_symbol.get(symbol, {})
        if not reference:
            continue

        adjusted = apply_adjustments(bars, actions)

        # Both series are defined only up to a scale factor, since a backward adjustment
        # anchors on the final bar. Normalize on the last common session before comparing.
        common = [b.session for b in adjusted if b.session in reference]
        if not common:
            continue
        anchor = common[-1]
        engine_anchor = next(float(b.close) for b in adjusted if b.session == anchor)
        provider_anchor = reference[anchor]
        if engine_anchor <= 0 or provider_anchor <= 0:
            continue
        scale = provider_anchor / engine_anchor

        errors: list[float] = []
        for bar in adjusted:
            provider = reference.get(bar.session)
            if provider is None or provider <= 0:
                continue
            engine = float(bar.close) * scale
            errors.append(abs(engine - provider) / provider)

        if not errors:
            continue

        median_error = _median(errors)
        worst_error = max(errors)
        splits = sum(1 for a in actions if a.action_type == CorporateActionType.SPLIT)
        dividends = sum(1 for a in actions if a.action_type == CorporateActionType.DIVIDEND)
        passed = median_error <= MEDIAN_TOLERANCE and worst_error <= WORST_CASE_TOLERANCE

        results.append(
            {
                "symbol": symbol,
                "sessions": len(errors),
                "splits": splits,
                "dividends": dividends,
                "median_rel_error": median_error,
                "max_rel_error": worst_error,
                "passed": passed,
            }
        )
        if not passed:
            failures.append(
                f"{symbol}: median {median_error:.4%}, worst {worst_error:.4%} "
                f"({splits} splits, {dividends} dividends)"
            )

    if not results:
        print("No comparable series found", file=sys.stderr)
        return 1

    passed_count = sum(1 for r in results if r["passed"])
    median_of_medians = _median([float(r["median_rel_error"]) for r in results])
    worst_overall = max(float(r["max_rel_error"]) for r in results)
    total_splits = sum(int(r["splits"]) for r in results)
    total_dividends = sum(int(r["dividends"]) for r in results)
    total_sessions = sum(int(r["sessions"]) for r in results)

    print(f"Instruments compared      : {len(results)}")
    print(f"Sessions compared         : {total_sessions:,}")
    print(f"Corporate actions replayed: {total_splits} splits, {total_dividends} dividends")
    print(f"Median relative error     : {median_of_medians:.4%}")
    print(f"Worst single-bar error    : {worst_overall:.4%}")
    print(f"Instruments within tolerance: {passed_count}/{len(results)}")

    worst_five = sorted(results, key=lambda r: float(r["median_rel_error"]), reverse=True)[:5]
    print("-" * 78)
    print("Largest median disagreements:")
    for row in worst_five:
        print(
            f"  {str(row['symbol']):<6} median {float(row['median_rel_error']):.4%}  "
            f"worst {float(row['max_rel_error']):.4%}  "
            f"({row['splits']} splits, {row['dividends']} dividends)"
        )

    report_path = REPO_ROOT / "artifacts" / "latest" / "market-data-verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "fixture": fixture_dir.name,
                "instruments": len(results),
                "sessions_compared": total_sessions,
                "splits_replayed": total_splits,
                "dividends_replayed": total_dividends,
                "median_relative_error": median_of_medians,
                "max_relative_error": worst_overall,
                "instruments_within_tolerance": passed_count,
                "median_tolerance": MEDIAN_TOLERANCE,
                "worst_case_tolerance": WORST_CASE_TOLERANCE,
                "per_instrument": results,
            },
            handle,
            indent=2,
        )
    print("-" * 78)
    print(f"Report written to {report_path.relative_to(REPO_ROOT)}")

    if failures:
        print(f"\nFAIL: {len(failures)} instrument(s) outside tolerance", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("PASS: engine adjustment reproduces the provider series within tolerance")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="us_research", help="Fixture directory name")
    args = parser.parse_args(argv)
    return verify(REPO_ROOT / "data" / "fixtures" / args.fixture)


if __name__ == "__main__":
    raise SystemExit(main())
