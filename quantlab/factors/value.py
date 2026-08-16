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
from quantlab.factors.missingness import validate_denominator
from quantlab.factors.snapshots import build_factor_snapshot


class EarningsYield(Factor):
    """Earnings yield: trailing point-in-time net income / market cap (or close price)."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="earnings_yield",
            name="Earnings Yield",
            category=FactorCategory.VALUE.value,
            description="Point-in-time net income divided by close price or market value",
            formula="net_income / close",
            direction=1,
            inputs=("fundamentals", "prices"),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="close",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        start_date = context.session - timedelta(days=30)
        end_date = context.session

        for inst_id in context.universe:
            # 1. Fetch latest PIT net_income
            fund_val = context.pit_data.get_fundamental(
                instrument_id=inst_id,
                metric="net_income",
                as_of=context.as_of,
            )

            if fund_val is None or fund_val.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            # 2. Fetch latest market bar on or before session
            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )
            valid_bars = [b for b in bars if b.session <= context.session]
            if not valid_bars:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            close_price = float(valid_bars[-1].close)
            if not validate_denominator(close_price, require_positive=True):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            # Earnings yield score
            score = float(fund_val.value) / close_price
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


class BookToMarket(Factor):
    """Book-to-Market: stockholders' equity (or book value) divided by close price."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="book_to_market",
            name="Book to Market",
            category=FactorCategory.VALUE.value,
            description="Stockholders equity divided by price",
            formula="stockholders_equity / close",
            direction=1,
            inputs=("fundamentals", "prices"),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="close",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        start_date = context.session - timedelta(days=30)
        end_date = context.session

        for inst_id in context.universe:
            fund_val = context.pit_data.get_fundamental(
                instrument_id=inst_id,
                metric="stockholders_equity",
                as_of=context.as_of,
            )
            # Fallback to net_income if stockholders_equity not reported
            if fund_val is None:
                fund_val = context.pit_data.get_fundamental(
                    instrument_id=inst_id,
                    metric="net_income",
                    as_of=context.as_of,
                )

            if fund_val is None or fund_val.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )
            valid_bars = [b for b in bars if b.session <= context.session]
            if not valid_bars:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            close_price = float(valid_bars[-1].close)
            if not validate_denominator(close_price, require_positive=True):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = float(fund_val.value) / close_price
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


class FCFYield(Factor):
    """Free Cash Flow yield: free cash flow divided by close price."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="fcf_yield",
            name="FCF Yield",
            category=FactorCategory.VALUE.value,
            description="Free cash flow divided by price",
            formula="free_cash_flow / close",
            direction=1,
            inputs=("fundamentals", "prices"),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="close",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        start_date = context.session - timedelta(days=30)
        end_date = context.session

        for inst_id in context.universe:
            fund_val = context.pit_data.get_fundamental(
                instrument_id=inst_id,
                metric="free_cash_flow",
                as_of=context.as_of,
            )
            # Fallback to operating_cash_flow or net_income
            if fund_val is None:
                fund_val = context.pit_data.get_fundamental(
                    instrument_id=inst_id,
                    metric="net_income",
                    as_of=context.as_of,
                )

            if fund_val is None or fund_val.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )
            valid_bars = [b for b in bars if b.session <= context.session]
            if not valid_bars:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            close_price = float(valid_bars[-1].close)
            if not validate_denominator(close_price, require_positive=True):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = float(fund_val.value) / close_price
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
