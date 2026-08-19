"""Two datasets holding the same ticker must not overwrite each other's prices.

Instrument ids are derived from the symbol, so AAPL resolves to the same id in every
dataset. When bar partitions shared one namespace, building a second dataset containing
AAPL replaced the first dataset's AAPL prices for the overlapping years - and every
factor score, backtest fill, and performance metric downstream was then computed on a
blend of two datasets, with nothing raising.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from quantlab.application.dataset_service import DatasetService
from quantlab.data.datasets import DatasetUniverseResolver
from quantlab.data.market_bars import MarketBarStore
from quantlab.domain.market import BarPriceSemantic
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore

SESSIONS = [date(2020, 1, d) for d in (2, 3, 6, 7, 8)]


def _write_fixture(source: Path, price: float) -> None:
    source.mkdir(parents=True, exist_ok=True)

    with open(source / "listings.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["symbol", "name", "exchange", "listed_date", "delisted_date", "is_etf", "sector"]
        )
        writer.writerow(["AAPL", "Apple Inc.", "NASDAQ", "1980-12-12", "", "False", "TECHNOLOGY"])

    with open(source / "prices.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        for session in SESSIONS:
            writer.writerow(
                [
                    session.isoformat(),
                    "AAPL",
                    f"{price:.2f}",
                    f"{price * 1.01:.2f}",
                    f"{price * 0.99:.2f}",
                    f"{price:.2f}",
                    "1000000",
                ]
            )


def _write_config(root: Path, dataset_id: str, source: Path) -> Path:
    config = root / f"{dataset_id}.yaml"
    config.write_text(
        "\n".join(
            [
                f"dataset_id: {dataset_id}",
                "version: v001",
                f"source_dir: {source.relative_to(root).as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    return config


def _closes(root: Path, dataset_id: str) -> list[float]:
    store = LocalAnalyticalStore(root / "data")
    resolver = DatasetUniverseResolver(store)
    instrument = resolver.members(dataset_id)[0].instrument_id
    bar_store = MarketBarStore(store, MarketBarStore.namespace_for(dataset_id))
    bars = bar_store.get_bars(instrument, SESSIONS[0], SESSIONS[-1], BarPriceSemantic.RAW)
    return [float(bar.close) for bar in bars]


def test_second_dataset_does_not_overwrite_the_first(tmp_path: Path) -> None:
    first_source = tmp_path / "data" / "fixtures" / "alpha" / "source"
    second_source = tmp_path / "data" / "fixtures" / "beta" / "source"
    _write_fixture(first_source, 100.0)
    _write_fixture(second_source, 250.0)

    service = DatasetService(base_dir=tmp_path)
    service.build_dataset(_write_config(tmp_path, "DATASET-ALPHA", first_source))
    service.build_dataset(_write_config(tmp_path, "DATASET-BETA", second_source))

    assert _closes(tmp_path, "DATASET-ALPHA") == [100.0] * len(SESSIONS)
    assert _closes(tmp_path, "DATASET-BETA") == [250.0] * len(SESSIONS)


def test_rebuilding_the_first_dataset_leaves_the_second_alone(tmp_path: Path) -> None:
    first_source = tmp_path / "data" / "fixtures" / "alpha" / "source"
    second_source = tmp_path / "data" / "fixtures" / "beta" / "source"
    _write_fixture(first_source, 100.0)
    _write_fixture(second_source, 250.0)

    service = DatasetService(base_dir=tmp_path)
    alpha_config = _write_config(tmp_path, "DATASET-ALPHA", first_source)
    service.build_dataset(alpha_config)
    service.build_dataset(_write_config(tmp_path, "DATASET-BETA", second_source))
    service.build_dataset(alpha_config)

    assert _closes(tmp_path, "DATASET-BETA") == [250.0] * len(SESSIONS)
