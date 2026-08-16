from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.common.errors import QuantLabError
from quantlab.data.corporate_actions import (
    CorporateActionStore,
    apply_adjustments,
)
from quantlab.data.market_bars import MarketBarStore
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.instrument_repository import InstrumentRepository


class NormalizationError(QuantLabError):
    """Raised when raw market data or actions fail normalization and validation."""


class NormalizationPipeline:
    def __init__(
        self,
        bar_store: MarketBarStore,
        action_store: CorporateActionStore,
    ) -> None:
        self._bar_store = bar_store
        self._action_store = action_store

    def normalize_eod_and_actions(
        self,
        raw_prices: str | bytes,
        raw_actions: str | bytes,
        resolver: InstrumentRepository,
        default_exchange: str = "NASDAQ",
    ) -> tuple[int, int]:
        prices_content = raw_prices.decode("utf-8") if isinstance(raw_prices, bytes) else raw_prices
        actions_content = (
            raw_actions.decode("utf-8") if isinstance(raw_actions, bytes) else raw_actions
        )

        # 1. Parse and store Corporate Actions first
        actions_reader = csv.DictReader(io.StringIO(actions_content))
        actions_by_inst: dict[InstrumentId, list[CorporateAction]] = {}
        action_count = 0

        for row in actions_reader:
            sym = row["symbol"].strip().upper()
            eff_date = date.fromisoformat(row["effective_date"].strip())

            # Calendar validation: weekday check
            if eff_date.weekday() >= 5:
                raise NormalizationError(f"Action effective_date on weekend: {eff_date}")

            inst_id = resolver.resolve(sym, default_exchange, eff_date)
            if inst_id is None:
                raise NormalizationError(
                    f"Unable to resolve instrument for action {sym} on {eff_date}"
                )

            action_type_str = row["action_type"].strip().lower()
            try:
                action_type = CorporateActionType(action_type_str)
            except ValueError as err:
                msg = f"Unknown corporate action type: {action_type_str}"
                raise NormalizationError(msg) from err

            announced_at = (
                datetime.fromisoformat(row["announced_at"]).replace(tzinfo=UTC)
                if "announced_at" in row and row["announced_at"]
                else datetime(eff_date.year, eff_date.month, eff_date.day, 9, 0, tzinfo=UTC)
            )
            available_at = (
                datetime.fromisoformat(row["available_at"]).replace(tzinfo=UTC)
                if "available_at" in row and row["available_at"]
                else announced_at
            )

            ratio_val = Decimal(str(row["ratio"])) if row.get("ratio") else None
            cash_val = Decimal(str(row["cash_amount"])) if row.get("cash_amount") else None

            action = CorporateAction(
                instrument_id=inst_id,
                action_type=action_type,
                effective_at=eff_date,
                announced_at=announced_at,
                available_at=available_at,
                ratio=ratio_val,
                cash_amount=cash_val,
                source=row.get("source", "raw_provider"),
            )
            self._action_store.record_action(action)
            actions_by_inst.setdefault(inst_id, []).append(action)
            action_count += 1

        # 2. Parse and validate Raw Daily Market Bars
        prices_reader = csv.DictReader(io.StringIO(prices_content))
        raw_bars_by_inst: dict[InstrumentId, list[MarketBar]] = {}
        bar_count = 0

        for row_idx, row in enumerate(prices_reader, start=1):
            sym = row["symbol"].strip().upper()
            session = date.fromisoformat(row["date"].strip())

            # Calendar validation
            if session.weekday() >= 5:
                raise NormalizationError(
                    f"Bar on weekend: {session} for symbol {sym} at row {row_idx}"
                )

            # Check for missing values (e.g. empty string)
            for col in ("open", "high", "low", "close", "volume"):
                val = row.get(col, "").strip()
                if not val:
                    msg = (
                        f"Missing required price field '{col}' for symbol {sym} "
                        f"on {session} at row {row_idx}"
                    )
                    raise NormalizationError(msg)

            try:
                op = Decimal(row["open"].strip())
                hi = Decimal(row["high"].strip())
                lo = Decimal(row["low"].strip())
                cl = Decimal(row["close"].strip())
                vol = Decimal(row["volume"].strip())
            except Exception as err:
                raise NormalizationError(f"Invalid decimal value in row {row_idx}: {err}") from err

            inst_id = resolver.resolve(sym, default_exchange, session)
            if inst_id is None:
                raise NormalizationError(
                    f"Unable to resolve instrument for price row {sym} on {session}"
                )

            observed_at = (
                datetime.fromisoformat(row["observed_at"]).replace(tzinfo=UTC)
                if "observed_at" in row and row["observed_at"]
                else datetime(session.year, session.month, session.day, 21, 0, tzinfo=UTC)
            )

            try:
                raw_bar = MarketBar(
                    instrument_id=inst_id,
                    session=session,
                    observed_at=observed_at,
                    open=op,
                    high=hi,
                    low=lo,
                    close=cl,
                    volume=vol,
                    semantic=BarPriceSemantic.RAW,
                    source=row.get("source", "raw_provider"),
                )
            except (ValueError, TypeError) as err:
                raise NormalizationError(f"Bar validation failed at row {row_idx}: {err}") from err

            raw_bars_by_inst.setdefault(inst_id, []).append(raw_bar)
            bar_count += 1

        # 3. Write RAW and ADJUSTED bars to MarketBarStore
        for target_id, bars in raw_bars_by_inst.items():
            self._bar_store.write_daily_bars(bars)
            inst_actions = actions_by_inst.get(target_id, [])
            adj_bars = apply_adjustments(bars, inst_actions)
            self._bar_store.write_daily_bars(adj_bars)

        return (bar_count, action_count)
