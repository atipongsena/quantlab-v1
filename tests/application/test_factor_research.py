"""Tests for FactorResearchService application workflows."""

import tempfile
import uuid
from datetime import date
from pathlib import Path

from quantlab.application.factor_research import FactorResearchService
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
)
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


def test_factor_research_service_list() -> None:
    service = FactorResearchService()
    factors = service.list_factors()
    assert len(factors) >= 14
    ids = {f["factor_id"] for f in factors}
    assert "momentum_12_1" in ids
    assert "roe" in ids
    assert "volatility_60d" in ids
    assert "earnings_yield" in ids


def test_factor_research_service_run_pipeline() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_path = root / "artifacts" / "quantlab.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = DatabaseEngine(DatabaseConfig(url=f"sqlite:///{db_path}"))

        # Setup instrument tables
        with engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS instruments (
                    instrument_id TEXT PRIMARY KEY,
                    issuer_name TEXT NOT NULL,
                    security_name TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    active_from TEXT NOT NULL,
                    active_to TEXT,
                    status TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS instrument_symbol_history (
                    instrument_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    source TEXT NOT NULL
                )
                """
            )

        repo = SqlInstrumentRepository(engine)
        inst_id = InstrumentId(uuid.uuid4())
        inst = Instrument(
            instrument_id=inst_id,
            issuer_name="Apple Inc",
            security_name="Common Stock",
            instrument_type=InstrumentType.EQUITY,
            exchange="NASDAQ",
            currency="USD",
            active_from=date(2010, 1, 1),
            active_to=None,
            status=InstrumentStatus.ACTIVE,
        )
        repo.upsert_identity(inst)

        service = FactorResearchService(base_dir=root, db_engine=engine)
        result = service.run_factor_research(
            factor_id="momentum_12_1",
            dataset_id="DATASET-v001",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )

        assert result.factor_id == "momentum_12_1"
        assert result.diagnostic_label == "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"
        assert "ic_mean" in result.as_dict()
