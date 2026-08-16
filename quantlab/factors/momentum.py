"""Momentum factor calculators."""

from __future__ import annotations

from datetime import timedelta

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import (
    Factor,
    FactorCategory,
    FactorContext,
    FactorDefinition,
    FactorSnapshot,
    FactorValue,
    MissingReason,
)
from quantlab.factors.snapshots import build_factor_snapshot


class Momentum12M1M(Factor):
    """12-month momentum minus 1-month reversal window (252 sessions lookback, 21 skip)."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="momentum_12_1",
            name="12M-1M Momentum",
            category=FactorCategory.MOMENTUM.value,
            description="12-month price momentum skipping the most recent 1 month",
            formula="(close[-21] / close[-252]) - 1",
            direction=1,
            inputs=("prices",),
            lookback_sessions=252,
            availability_lag_sessions=0,
            missingness_policy="insufficient_history",
            price_semantic="total_return",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        # Fetch bars over lookback period (approx 400 calendar days for 252 sessions)
        start_date = context.session - timedelta(days=450)
        end_date = context.session
        values: dict[InstrumentId, FactorValue] = {}

        for inst_id in context.universe:
            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )

            # Filter bars on or before session
            valid_bars = [b for b in bars if b.session <= context.session]

            if len(valid_bars) < 252:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            # close[-21] and close[-252]
            p_recent = float(valid_bars[-21].close)
            p_base = float(valid_bars[-252].close)

            if p_base <= 0:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = (p_recent / p_base) - 1.0
            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=score,
                missing_reason=None,
            )

        return build_factor_snapshot(
            factor_id=self._def.factor_id,
            version=self._def.calculator_version,
            session=context.session,
            as_of=context.as_of,
            raw_values=values,
            universe=context.universe,
        )


class Momentum6M1M(Factor):
    """6-month momentum minus 1-month reversal window (126 sessions lookback, 21 skip)."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="momentum_6_1",
            name="6M-1M Momentum",
            category=FactorCategory.MOMENTUM.value,
            description="6-month price momentum skipping the most recent 1 month",
            formula="(close[-21] / close[-126]) - 1",
            direction=1,
            inputs=("prices",),
            lookback_sessions=126,
            availability_lag_sessions=0,
            missingness_policy="insufficient_history",
            price_semantic="total_return",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        start_date = context.session - timedelta(days=250)
        end_date = context.session
        values: dict[InstrumentId, FactorValue] = {}

        for inst_id in context.universe:
            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )

            valid_bars = [b for b in bars if b.session <= context.session]

            if len(valid_bars) < 126:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            p_recent = float(valid_bars[-21].close)
            p_base = float(valid_bars[-126].close)

            if p_base <= 0:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = (p_recent / p_base) - 1.0
            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=score,
                missing_reason=None,
            )

        return build_factor_snapshot(
            factor_id=self._def.factor_id,
            version=self._def.calculator_version,
            session=context.session,
            as_of=context.as_of,
            raw_values=values,
            universe=context.universe,
        )
