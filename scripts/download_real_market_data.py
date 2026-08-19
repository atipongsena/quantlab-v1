"""Download real US market history and write it in QuantLab's fixture format.

Two details matter more than anything else in this script.

First, Yahoo's ``Close`` column is already split-adjusted even when ``auto_adjust`` is
off. Writing it out as a raw price and *also* recording the split as a corporate action
makes the engine apply the same split twice. This script un-applies the split history to
recover the as-traded price, so the engine's own adjustment reproduces the provider's
series instead of doubling it.

Second, the splits and dividends written here are the provider's real action history,
not placeholders. ``scripts/verify_market_data.py`` re-derives the total-return series
from raw price plus actions and compares it against Yahoo's independently computed
``Adj Close``; that comparison is the check that both halves are consistent.

Usage:
    python scripts/download_real_market_data.py \
        --universe configs/universes/us-research-v1.yaml \
        --start 1995-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_universe(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Universe config at {path} is not a mapping")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_count(path: Path) -> int:
    with open(path, encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _split_unadjust_factor(index: pd.Index, splits: pd.Series) -> pd.Series:
    """Per-bar multiplier that converts a split-adjusted quote back to as-traded.

    A bar on date *t* was quoted before every split effective after *t*, so its true
    price is the adjusted price multiplied by the product of those later split ratios.
    """
    factor = pd.Series(1.0, index=index)

    ratio_by_day: dict[date, float] = {}
    if splits is not None and len(splits) > 0:
        for timestamp, ratio in splits.items():
            value = float(ratio)
            if value > 0:
                day = timestamp.date()
                ratio_by_day[day] = ratio_by_day.get(day, 1.0) * value

    if ratio_by_day:
        cumulative = 1.0
        for idx in range(len(index) - 1, -1, -1):
            bar_day = index[idx].date()
            factor.iloc[idx] = cumulative
            # A split effective on this session leaves this bar already post-split, but
            # every earlier bar was quoted pre-split and must carry the ratio.
            cumulative *= ratio_by_day.get(bar_day, 1.0)

    return factor


def _write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def download(
    universe_path: Path,
    start: str,
    end: str,
    out_dir: Path,
) -> int:
    universe = _load_universe(universe_path)
    equities = list(universe.get("equities") or [])
    etfs = list(universe.get("etfs") or [])
    members = [(entry, False) for entry in equities] + [(entry, True) for entry in etfs]
    if not members:
        print(f"Universe {universe_path} declares no instruments", file=sys.stderr)
        return 1

    print(
        f"Universe {universe.get('universe_id', universe_path.stem)}: "
        f"{len(equities)} equities + {len(etfs)} ETFs, window {start} to {end}"
    )

    listing_rows: list[list[object]] = []
    price_rows: list[list[object]] = []
    action_rows: list[list[object]] = []
    reference_rows: list[list[object]] = []
    coverage: list[dict[str, object]] = []
    failures: list[str] = []

    for entry, is_etf in members:
        symbol = str(entry["symbol"]).upper()
        exchange = str(entry.get("exchange", "NYSE")).upper()
        sector = str(entry.get("sector", "UNKNOWN")).upper()

        try:
            ticker = yf.Ticker(symbol)
            frame = ticker.history(start=start, end=end, auto_adjust=False, actions=True)
        except Exception as err:  # noqa: BLE001 - provider errors are reported, not raised
            failures.append(f"{symbol}: {err}")
            continue

        if frame is None or frame.empty:
            failures.append(f"{symbol}: provider returned no rows")
            continue

        frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
        if frame.empty:
            failures.append(f"{symbol}: no usable OHLC rows")
            continue

        splits = frame["Stock Splits"] if "Stock Splits" in frame else pd.Series(dtype=float)
        splits = splits[splits > 0]
        dividends = frame["Dividends"] if "Dividends" in frame else pd.Series(dtype=float)
        dividends = dividends[dividends > 0]

        # Yahoo reports both prices and dividend amounts in post-split terms. Reverse the
        # split adjustment on both together, otherwise a $0.50 dividend paid before a 4:1
        # split gets divided against an as-traded price four times larger and the
        # dividend adjustment silently shrinks to a quarter of its true size.
        unadjust = _split_unadjust_factor(frame.index, splits)
        raw = frame.copy()
        for column in ("Open", "High", "Low", "Close"):
            raw[column] = raw[column] * unadjust
        raw["Volume"] = raw["Volume"] / unadjust
        raw_dividends = dividends * unadjust.reindex(dividends.index).fillna(1.0)

        first_session = frame.index[0].date()
        last_session = frame.index[-1].date()

        listing_rows.append(
            [
                symbol,
                str(entry.get("name", symbol)),
                exchange,
                first_session.isoformat(),
                "",
                str(is_etf),
                sector,
            ]
        )

        for timestamp, row in raw.iterrows():
            session = timestamp.date()
            open_p, high_p, low_p, close_p = (
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
            )
            if min(open_p, high_p, low_p, close_p) <= 0:
                continue
            volume = row["Volume"]
            volume_i = int(volume) if volume == volume else 0  # noqa: PLR0124 - NaN check
            price_rows.append(
                [
                    session.isoformat(),
                    symbol,
                    f"{open_p:.6f}",
                    f"{high_p:.6f}",
                    f"{low_p:.6f}",
                    f"{close_p:.6f}",
                    volume_i,
                ]
            )

        for timestamp, adjusted_close in frame["Adj Close"].items():
            if adjusted_close == adjusted_close and adjusted_close > 0:  # noqa: PLR0124
                reference_rows.append(
                    [timestamp.date().isoformat(), symbol, f"{float(adjusted_close):.6f}"]
                )

        # Corporate actions become known the evening before they take effect.
        for timestamp, ratio in splits.items():
            effective = timestamp.date()
            action_rows.append(
                [
                    effective.isoformat(),
                    f"{effective.isoformat()} 00:00:00",
                    symbol,
                    "SPLIT",
                    f"{float(ratio):.8f}",
                    "",
                ]
            )
        for timestamp, amount in raw_dividends.items():
            effective = timestamp.date()
            action_rows.append(
                [
                    effective.isoformat(),
                    f"{effective.isoformat()} 00:00:00",
                    symbol,
                    "DIVIDEND",
                    "",
                    f"{float(amount):.6f}",
                ]
            )

        coverage.append(
            {
                "symbol": symbol,
                "sector": sector,
                "is_etf": is_etf,
                "first_session": first_session.isoformat(),
                "last_session": last_session.isoformat(),
                "sessions": int(len(raw)),
                "splits": int(len(splits)),
                "dividends": int(len(dividends)),
            }
        )
        print(
            f"  {symbol:<6} {len(raw):>6} sessions  {first_session} -> {last_session}  "
            f"splits={len(splits)} dividends={len(dividends)}"
        )

    if not price_rows:
        print("No price data downloaded", file=sys.stderr)
        return 1

    price_rows.sort(key=lambda r: (str(r[0]), str(r[1])))
    action_rows.sort(key=lambda r: (str(r[0]), str(r[2])))
    reference_rows.sort(key=lambda r: (str(r[0]), str(r[1])))

    _write_csv(
        out_dir / "listings.csv",
        ["symbol", "name", "exchange", "listed_date", "delisted_date", "is_etf", "sector"],
        listing_rows,
    )
    _write_csv(
        out_dir / "prices.csv",
        ["date", "symbol", "open", "high", "low", "close", "volume"],
        price_rows,
    )
    _write_csv(
        out_dir / "actions.csv",
        ["effective_date", "available_at", "symbol", "action_type", "ratio", "cash_amount"],
        action_rows,
    )
    _write_csv(
        out_dir / "reference_adjusted_close.csv",
        ["date", "symbol", "adj_close"],
        reference_rows,
    )

    sessions = sorted({str(row[0]) for row in price_rows})
    manifest = {
        "universe_id": universe.get("universe_id", universe_path.stem),
        "universe_config": str(universe_path.relative_to(REPO_ROOT)),
        "provider": "yahoo-finance (yfinance)",
        "requested_window": {"start": start, "end": end},
        "downloaded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "session_span": {"first": sessions[0], "last": sessions[-1], "count": len(sessions)},
        "instruments": len(coverage),
        "equities": sum(1 for c in coverage if not c["is_etf"]),
        "etfs": sum(1 for c in coverage if c["is_etf"]),
        "survivorship_bias": universe.get("survivorship_bias", "PRESENT"),
        "survivorship_note": universe.get("survivorship_note", ""),
        "price_semantic": "raw as-traded (provider split adjustment reversed)",
        "failures": failures,
        "coverage": coverage,
        "source_files": {},
    }
    for name in (
        "listings.csv",
        "prices.csv",
        "actions.csv",
        "reference_adjusted_close.csv",
    ):
        path = out_dir / name
        manifest["source_files"][name] = {
            "sha256": _sha256(path),
            "byte_count": path.stat().st_size,
            "row_count": _row_count(path),
        }

    with open(out_dir / "download_manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(
        f"\nWrote {len(price_rows)} bars for {len(coverage)} instruments "
        f"({sessions[0]} to {sessions[-1]}, {len(sessions)} sessions) into {out_dir}"
    )
    print(f"Corporate actions: {len(action_rows)} splits and dividends")
    if failures:
        print(f"{len(failures)} instrument(s) failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--universe",
        default="configs/universes/us-research-v1.yaml",
        help="Path to the universe YAML",
    )
    parser.add_argument("--start", default="1995-01-01", help="First session to request")
    parser.add_argument(
        "--end",
        default=date.today().isoformat(),
        help="Exclusive end of the request window",
    )
    parser.add_argument(
        "--out",
        default="data/fixtures/us_research/source",
        help="Directory to write the fixture CSVs into",
    )
    args = parser.parse_args(argv)

    universe_path = Path(args.universe)
    if not universe_path.is_absolute():
        universe_path = REPO_ROOT / universe_path
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    return download(universe_path, args.start, args.end, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
