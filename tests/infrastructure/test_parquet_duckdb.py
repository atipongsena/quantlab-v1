from __future__ import annotations

from pathlib import Path

import pytest

from quantlab.infrastructure.duckdb import AnalyticalQueryError, LocalAnalyticalStore
from quantlab.infrastructure.parquet import read_partition, write_partition


def test_parquet_partition_write_and_roundtrip(tmp_path: Path) -> None:
    rows = [
        {"session": "2024-01-02", "symbol": "AAPL", "close": 185.5, "volume": 1000},
        {"session": "2024-01-03", "symbol": "AAPL", "close": 184.2, "volume": 1200},
    ]
    schema = {"session": "string", "symbol": "string", "close": "float", "volume": "int"}

    ref = write_partition(
        base_dir=tmp_path / "data",
        dataset_id="DATASET-v001",
        table_name="market_bars",
        partition_key="2024_01",
        rows=rows,
        schema=schema,
    )

    assert ref.row_count == 2
    assert ref.dataset_id == "DATASET-v001"
    assert ref.table_name == "market_bars"

    loaded_rows = read_partition(ref)
    assert len(loaded_rows) == 2
    assert loaded_rows[0]["symbol"] == "AAPL"
    assert float(str(loaded_rows[0]["close"])) == 185.5


def test_duckdb_analytical_store_queries_and_read_only_enforcement(tmp_path: Path) -> None:
    store = LocalAnalyticalStore(tmp_path / "analytics")

    rows = [
        {"session": "2024-01-02", "symbol": "AAPL", "close": 185.5},
        {"session": "2024-01-02", "symbol": "MSFT", "close": 375.0},
        {"session": "2024-01-03", "symbol": "AAPL", "close": 186.0},
    ]

    ref = store.write_partition(
        dataset_id="DATASET-v001",
        table="market_bars",
        partition_key="2024_01",
        data=rows,
    )

    # Read-only query execution
    results = store.query(
        "SELECT symbol, count(*) as cnt FROM market_bars GROUP BY symbol ORDER BY symbol",
        refs=[ref],
    )
    assert len(results) == 2
    assert results[0]["symbol"] == "AAPL"
    assert int(results[0]["cnt"]) == 2

    # Mutation query rejected
    with pytest.raises(AnalyticalQueryError, match="rejected modifying SQL"):
        store.query("DROP TABLE market_bars", refs=[ref])

    with pytest.raises(AnalyticalQueryError, match="rejected modifying SQL"):
        store.query("DELETE FROM market_bars", refs=[ref])
