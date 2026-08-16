from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

import yaml  # type: ignore[import-untyped]

from migrations.env import run_migrations
from quantlab.common.hashing import canonical_hash
from quantlab.data.corporate_actions import (
    SqlCorporateActionStore,
    apply_adjustments,
)
from quantlab.data.datasets import DatasetManifest, DatasetPublisher
from quantlab.data.fundamentals import FundamentalValue, SqlFundamentalStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.quality import DataQualityAuditor
from quantlab.domain.corporate_actions import (
    CorporateAction,
    CorporateActionType,
)
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.artifacts import LocalArtifactStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.duckdb import LocalAnalyticalStore
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


class DatasetService:
    def __init__(
        self,
        base_dir: Path | None = None,
        db_engine: DatabaseEngine | None = None,
    ) -> None:
        self._base_dir = Path(base_dir or Path.cwd())
        db_path = self._base_dir / "artifacts" / "quantlab.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_engine = db_engine or DatabaseEngine(DatabaseConfig(url=f"sqlite:///{db_path}"))
        self._artifact_store = LocalArtifactStore(self._base_dir / "artifacts")
        self._analytical_store = LocalAnalyticalStore(self._base_dir / "data")

    def build_dataset(
        self,
        config_path: Path | str,
        offline: bool = True,
    ) -> DatasetManifest:
        config_p = Path(config_path)
        if not config_p.is_absolute():
            config_p = self._base_dir / config_p

        with open(config_p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        dataset_id = cfg.get("dataset_id", "DATASET-v001")
        version = cfg.get("version", "v001")
        source_dir_rel = cfg.get("source_dir", "data/fixtures/synthetic_v1/source")
        source_dir = Path(source_dir_rel)
        if not source_dir.is_absolute():
            source_dir = self._base_dir / source_dir

        # 1. Run migrations
        run_migrations(self._db_engine)

        inst_repo = SqlInstrumentRepository(self._db_engine)
        action_store = SqlCorporateActionStore(self._db_engine)
        fund_store = SqlFundamentalStore(self._db_engine)
        bar_store = MarketBarStore(self._analytical_store)

        # 2. Parse listings
        listings_file = source_dir / "listings.csv"
        symbol_to_inst_id: dict[str, InstrumentId] = {}
        instruments_data: list[dict[str, object]] = []
        symbol_history_data: list[dict[str, object]] = []

        if listings_file.exists():
            with open(listings_file, encoding="utf-8") as f:
                reader = list(csv.DictReader(f))

            for row in reader:
                sym = row["symbol"].strip().upper()
                # Deterministic UUID per symbol or entity
                if sym in ("FB", "META"):
                    # Shared company instrument
                    inst_uuid = uuid5(NAMESPACE_DNS, "quantlab.entity.meta_platforms")
                else:
                    inst_uuid = uuid5(NAMESPACE_DNS, f"quantlab.entity.{sym.lower()}")
                inst_id = InstrumentId.from_uuid(inst_uuid)
                symbol_to_inst_id[sym] = inst_id

                is_etf = row.get("is_etf", "False").strip().lower() in ("true", "1")
                itype = InstrumentType.ETF if is_etf else InstrumentType.EQUITY
                listed_dt = (
                    date.fromisoformat(row["listed_date"].strip())
                    if row.get("listed_date")
                    else date(1970, 1, 1)
                )
                delisted_dt = (
                    date.fromisoformat(row["delisted_date"].strip())
                    if row.get("delisted_date") and row["delisted_date"].strip()
                    else None
                )
                status = InstrumentStatus.DELISTED if delisted_dt else InstrumentStatus.ACTIVE
                exchange = row.get("exchange", "NASDAQ").strip().upper()

                inst = Instrument(
                    instrument_id=inst_id,
                    issuer_name=row["name"].strip(),
                    security_name=row["name"].strip(),
                    instrument_type=itype,
                    exchange=exchange,
                    currency="USD",
                    active_from=listed_dt,
                    active_to=delisted_dt,
                    status=status,
                )
                history = SymbolHistory(
                    instrument_id=inst_id,
                    symbol=sym,
                    exchange=exchange,
                    valid_from=listed_dt,
                    valid_to=delisted_dt,
                    source="fixture",
                )
                inst_repo.upsert_identity(inst, [history])

                instruments_data.append(
                    {
                        "instrument_id": str(inst_id.value),
                        "symbol": sym,
                        "name": inst.issuer_name,
                        "type": inst.instrument_type.value,
                        "exchange": exchange,
                        "active_from": listed_dt.isoformat(),
                        "active_to": delisted_dt.isoformat() if delisted_dt else "",
                        "status": status.value,
                    }
                )
                symbol_history_data.append(
                    {
                        "instrument_id": str(inst_id.value),
                        "symbol": sym,
                        "exchange": exchange,
                        "valid_from": listed_dt.isoformat(),
                        "valid_to": delisted_dt.isoformat() if delisted_dt else "",
                    }
                )

        # 3. Parse corporate actions
        actions_file = source_dir / "actions.csv"
        actions_data: list[dict[str, object]] = []
        if actions_file.exists():
            with open(actions_file, encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
            for row in reader:
                sym = row["symbol"].strip().upper()
                resolved_id = symbol_to_inst_id.get(sym)
                if resolved_id is None:
                    continue
                atype_str = row["action_type"].strip().upper()
                atype = CorporateActionType(atype_str.lower())
                ratio_str = row.get("ratio") or row.get("split_ratio") or ""
                ratio_val = Decimal(ratio_str.strip()) if ratio_str.strip() else None

                cash_str = row.get("cash_amount") or row.get("value") or ""
                cash_val = Decimal(cash_str.strip()) if cash_str.strip() else None
                eff_dt = date.fromisoformat(row["effective_date"].strip())
                ann_dt = datetime(eff_dt.year, eff_dt.month, eff_dt.day, 9, 0, tzinfo=UTC)
                action = CorporateAction(
                    instrument_id=resolved_id,
                    action_type=atype,
                    effective_at=eff_dt,
                    announced_at=ann_dt,
                    available_at=ann_dt,
                    ratio=ratio_val,
                    cash_amount=cash_val,
                    source="fixture",
                )
                action_store.record_action(action)
                actions_data.append(
                    {
                        "instrument_id": str(resolved_id.value),
                        "symbol": sym,
                        "action_type": atype.value,
                        "effective_date": eff_dt.isoformat(),
                        "ratio": str(ratio_val) if ratio_val else "",
                        "cash_amount": str(cash_val) if cash_val else "",
                    }
                )

        # 4. Parse fundamentals
        funds_file = source_dir / "fundamentals.csv"
        funds_data: list[dict[str, object]] = []
        if funds_file.exists():
            with open(funds_file, encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
            for row in reader:
                sym = row["symbol"].strip().upper()
                resolved_id = symbol_to_inst_id.get(sym)
                if resolved_id is None:
                    continue
                p_end = date.fromisoformat(row["period_end"].strip())
                f_date = (
                    date.fromisoformat(row["filing_date"].strip())
                    if "filing_date" in row and row["filing_date"].strip()
                    else p_end
                )
                avail_at = (
                    datetime.fromisoformat(row["available_at"].strip()).replace(tzinfo=UTC)
                    if "available_at" in row and row["available_at"].strip()
                    else datetime(f_date.year, f_date.month, f_date.day, 21, 0, tzinfo=UTC)
                )
                metric = row["metric"].strip().lower()
                val = Decimal(row["value"].strip())
                is_restated = row.get("is_restatement", "False").strip().lower() in (
                    "true",
                    "1",
                )
                source = row.get("source", "fixture")
                fv = FundamentalValue(
                    instrument_id=resolved_id,
                    period_end=p_end,
                    filing_date=f_date,
                    available_at=avail_at,
                    metric=metric,
                    value=val,
                    is_restatement=is_restated,
                    source=source,
                )
                fund_store.record_statement(fv)
                funds_data.append(
                    {
                        "instrument_id": str(resolved_id.value),
                        "symbol": sym,
                        "period_end": p_end.isoformat(),
                        "filing_date": f_date.isoformat(),
                        "available_at": avail_at.isoformat(),
                        "metric": metric,
                        "value": str(val),
                        "is_restatement": is_restated,
                    }
                )

        # 5. Parse market prices and write raw & adjusted bars
        prices_file = source_dir / "prices.csv"
        raw_bars: list[MarketBar] = []
        raw_bars_by_inst: dict[InstrumentId, list[MarketBar]] = {}
        prices_data: list[dict[str, object]] = []

        if prices_file.exists():
            with open(prices_file, encoding="utf-8") as f:
                reader = list(csv.DictReader(f))

            for row in reader:
                sym = row["symbol"].strip().upper()
                resolved_id = symbol_to_inst_id.get(sym)
                if resolved_id is None:
                    continue

                session = date.fromisoformat(row["date"].strip())
                close_str = row["close"].strip()
                if not close_str:
                    continue
                cl = Decimal(close_str)

                open_str = row.get("open", "").strip()
                op = Decimal(open_str) if open_str else cl  # Impute missing open from close

                high_str = row.get("high", "").strip()
                hi = Decimal(high_str) if high_str else max(op, cl)

                low_str = row.get("low", "").strip()
                lo = Decimal(low_str) if low_str else min(op, cl)

                vol_str = row.get("volume", "").strip()
                vol = Decimal(vol_str) if vol_str else Decimal("100000")

                observed_at = (
                    datetime.fromisoformat(row["observed_at"]).replace(tzinfo=UTC)
                    if "observed_at" in row and row["observed_at"]
                    else datetime(session.year, session.month, session.day, 21, 0, tzinfo=UTC)
                )

                bar = MarketBar(
                    instrument_id=resolved_id,
                    session=session,
                    observed_at=observed_at,
                    open=op,
                    high=hi,
                    low=lo,
                    close=cl,
                    volume=vol,
                    semantic=BarPriceSemantic.RAW,
                    source="fixture",
                )
                raw_bars.append(bar)
                raw_bars_by_inst.setdefault(resolved_id, []).append(bar)
                prices_data.append(
                    {
                        "instrument_id": str(resolved_id.value),
                        "symbol": sym,
                        "session": session.isoformat(),
                        "open": str(op),
                        "high": str(hi),
                        "low": str(lo),
                        "close": str(cl),
                        "volume": str(vol),
                    }
                )

        # Write raw bars
        bar_store.write_daily_bars(raw_bars)

        # Generate and write adjusted bars
        adjusted_bars: list[MarketBar] = []
        for inst_id, bars in raw_bars_by_inst.items():
            acts = action_store.get_actions(inst_id)
            adj_bars = apply_adjustments(bars, acts)
            adjusted_bars.extend(adj_bars)

        bar_store.write_daily_bars(adjusted_bars)

        # 6. Quality audit
        auditor = DataQualityAuditor()
        quality_report = auditor.audit_market_bars(
            dataset_id=dataset_id,
            bars=raw_bars,
        )

        # 7. Publish dataset
        publisher = DatasetPublisher(self._artifact_store, self._analytical_store)
        tables_map = {
            "instruments": instruments_data,
            "symbol_history": symbol_history_data,
            "prices": prices_data,
            "actions": actions_data,
            "fundamentals": funds_data,
        }
        manifest = publisher.publish(
            dataset_id=dataset_id,
            version=version,
            tables_data=tables_map,
            quality_report=quality_report,
        )

        # Also ensure manifest.json is written to artifacts/datasets/{dataset_id}/manifest.json
        manifest_dest = self._base_dir / "artifacts" / "datasets" / dataset_id / "manifest.json"
        manifest_dest.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_dest, "w", encoding="utf-8") as f:
            json.dump(manifest.as_dict(), f, indent=2)

        return manifest

    def inspect_dataset(
        self,
        dataset_id: str,
        verify_hash: bool = True,
    ) -> dict[str, object]:
        manifest_path = self._base_dir / "artifacts" / "datasets" / dataset_id / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")

        with open(manifest_path, encoding="utf-8") as f:
            manifest_dict = json.load(f)

        manifest_hash = manifest_dict.get("manifest_hash", "")
        payload_for_hash = {
            "dataset_id": manifest_dict.get("dataset_id"),
            "version": manifest_dict.get("version"),
            "tables": manifest_dict.get("tables"),
            "row_counts": manifest_dict.get("row_counts"),
            "quality_report": manifest_dict.get("quality_report"),
        }
        computed_hash = canonical_hash(payload_for_hash)

        hash_verified = manifest_hash == computed_hash if verify_hash else True
        status = "PASS" if hash_verified else "FAIL"

        return {
            "dataset_id": dataset_id,
            "version": manifest_dict.get("version"),
            "manifest_hash": manifest_hash,
            "computed_hash": computed_hash,
            "hash_verified": hash_verified,
            "status": status,
            "tables": manifest_dict.get("tables"),
            "row_counts": manifest_dict.get("row_counts"),
            "created_at": manifest_dict.get("created_at"),
        }
