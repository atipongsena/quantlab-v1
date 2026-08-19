"""Building the same dataset twice must not change what it contains.

A repeated ingest that appends corporate actions is silent and catastrophic: a doubled
4:1 split adjusts every earlier price by 16 instead of 4, so returns, factor scores, and
backtest equity all shift while every gate still reports PASS.
"""

from __future__ import annotations

import csv
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from quantlab.application.dataset_service import DatasetService
from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.fundamentals import SqlFundamentalStore
from quantlab.data.macro import SqlMacroStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.pit_facade import PointInTimeDataFacade
from quantlab.domain.identity import InstrumentId
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository
from quantlab.universe.membership import UniverseEngine

SPLIT_RATIO = 4
DATASET_ID = "DATASET-IDEMPOTENT-TEST"


def _write_fixture(source: Path) -> None:
    source.mkdir(parents=True, exist_ok=True)

    with open(source / "listings.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["symbol", "name", "exchange", "listed_date", "delisted_date", "is_etf", "sector"]
        )
        writer.writerow(["ZZZ", "Zeta Corp", "NASDAQ", "2019-01-01", "", "False", "TECHNOLOGY"])

    # A flat $400 price that halves-and-halves again across a 4:1 split on 2020-02-03.
    sessions = [date(2020, 1, d) for d in range(2, 6)] + [date(2020, 2, d) for d in range(3, 7)]
    with open(source / "prices.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        for session in sessions:
            price = 400.0 if session < date(2020, 2, 3) else 100.0
            writer.writerow(
                [
                    session.isoformat(),
                    "ZZZ",
                    f"{price:.2f}",
                    f"{price * 1.01:.2f}",
                    f"{price * 0.99:.2f}",
                    f"{price:.2f}",
                    "1000000",
                ]
            )

    with open(source / "actions.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["effective_date", "available_at", "symbol", "action_type", "ratio", "cash_amount"]
        )
        writer.writerow(["2020-02-03", "2020-02-02 20:00:00", "ZZZ", "SPLIT", "4.0", ""])


def _write_config(root: Path, source: Path) -> Path:
    config = root / "dataset.yaml"
    config.write_text(
        "\n".join(
            [
                f"dataset_id: {DATASET_ID}",
                "version: v001",
                "fixture: idempotent_test",
                f"source_dir: {source.relative_to(root).as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    return config


def _adjusted_closes(root: Path) -> list[float]:
    engine = DatabaseEngine(DatabaseConfig(url=f"sqlite:///{root / 'artifacts' / 'quantlab.db'}"))
    store = LocalAnalyticalStore(root / "data")
    instrument_repo = SqlInstrumentRepository(engine)
    bar_store = MarketBarStore(store, MarketBarStore.namespace_for(DATASET_ID))
    facade = PointInTimeDataFacade(
        instrument_repo=instrument_repo,
        bar_store=bar_store,
        action_store=SqlCorporateActionStore(engine),
        fund_store=SqlFundamentalStore(engine),
        macro_store=SqlMacroStore(engine),
        universe_engine=UniverseEngine(instrument_repo=instrument_repo, bar_store=bar_store),
    )
    instrument: InstrumentId = instrument_repo.list_all()[0].instrument_id
    bars = facade.get_market_bars(
        instrument_id=instrument,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 2, 28),
        as_of=datetime(2020, 3, 1, tzinfo=UTC),
        adjusted=True,
    )
    return [float(bar.close) for bar in bars]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    source = tmp_path / "data" / "fixtures" / "idempotent_test" / "source"
    _write_fixture(source)
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_rebuild_does_not_duplicate_corporate_actions(workspace: Path) -> None:
    config = _write_config(
        workspace, workspace / "data" / "fixtures" / "idempotent_test" / "source"
    )
    service = DatasetService(base_dir=workspace)

    service.build_dataset(config)
    first_closes = _adjusted_closes(workspace)

    service.build_dataset(config)
    second_closes = _adjusted_closes(workspace)

    assert first_closes, "the fixture produced no adjusted bars to compare"
    assert second_closes == first_closes, (
        "Rebuilding the dataset changed adjusted prices, which means the corporate "
        "action history was appended to rather than reconciled"
    )


def test_split_is_applied_exactly_once(workspace: Path) -> None:
    config = _write_config(
        workspace, workspace / "data" / "fixtures" / "idempotent_test" / "source"
    )
    DatasetService(base_dir=workspace).build_dataset(config)

    closes = _adjusted_closes(workspace)
    pre_split = closes[0]
    post_split = closes[-1]

    # $400 before a 4:1 split is $100 in post-split terms. Applying the split twice would
    # land on $25 and still look like a plausible price series.
    assert post_split == pytest.approx(100.0, rel=1e-6)
    assert pre_split == pytest.approx(post_split, rel=1e-6)
    assert pre_split == pytest.approx(400.0 / SPLIT_RATIO, rel=1e-6)


def test_action_row_count_is_stable_across_rebuilds(workspace: Path) -> None:
    config = _write_config(
        workspace, workspace / "data" / "fixtures" / "idempotent_test" / "source"
    )
    service = DatasetService(base_dir=workspace)
    service.build_dataset(config)
    service.build_dataset(config)

    engine = DatabaseEngine(
        DatabaseConfig(url=f"sqlite:///{workspace / 'artifacts' / 'quantlab.db'}")
    )
    with engine.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS n FROM corporate_actions")
        assert int(cursor.fetchone()["n"]) == 1
