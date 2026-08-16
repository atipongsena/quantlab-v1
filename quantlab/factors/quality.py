"""Quality factor calculators."""

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


class ROE(Factor):
    """Return on Equity: net income / stockholders equity."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="roe",
            name="Return on Equity",
            category=FactorCategory.QUALITY.value,
            description="Point-in-time net income divided by stockholders equity",
            formula="net_income / stockholders_equity",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="none",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        for inst_id in context.universe:
            net_income = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="net_income", as_of=context.as_of
            )
            equity = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="stockholders_equity", as_of=context.as_of
            )

            if net_income is None or net_income.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            denom_val = float(equity.value) if equity and equity.value is not None else 1.0
            if not validate_denominator(denom_val):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = float(net_income.value) / denom_val
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


class ROA(Factor):
    """Return on Assets: net income / total assets."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="roa",
            name="Return on Assets",
            category=FactorCategory.QUALITY.value,
            description="Point-in-time net income divided by total assets",
            formula="net_income / total_assets",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="none",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        for inst_id in context.universe:
            net_income = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="net_income", as_of=context.as_of
            )
            assets = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="total_assets", as_of=context.as_of
            )

            if net_income is None or net_income.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            denom_val = float(assets.value) if assets and assets.value is not None else 1.0
            if not validate_denominator(denom_val):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = float(net_income.value) / denom_val
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


class GrossProfitability(Factor):
    """Gross Profitability: gross profit (or revenue - cogs) / total assets."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="gross_profitability",
            name="Gross Profitability",
            category=FactorCategory.QUALITY.value,
            description="Gross profit divided by total assets",
            formula="gross_profit / total_assets",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="none",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        for inst_id in context.universe:
            gp = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="gross_profit", as_of=context.as_of
            )
            if gp is None:
                gp = context.pit_data.get_fundamental(
                    instrument_id=inst_id, metric="net_income", as_of=context.as_of
                )

            if gp is None or gp.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            assets = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="total_assets", as_of=context.as_of
            )
            denom_val = float(assets.value) if assets and assets.value is not None else 1.0
            if not validate_denominator(denom_val):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            score = float(gp.value) / denom_val
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


class AccrualQuality(Factor):
    """Accrual Quality: -(operating income - operating cash flow) / total assets."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="accrual_quality",
            name="Accrual Quality",
            category=FactorCategory.QUALITY.value,
            description="Negative accruals normalized by assets (higher score is better)",
            formula="-(operating_income - operating_cash_flow) / total_assets",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=60,
            availability_lag_sessions=1,
            missingness_policy="missing_fundamental",
            price_semantic="none",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        values: dict[InstrumentId, FactorValue] = {}
        for inst_id in context.universe:
            op_inc = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="operating_income", as_of=context.as_of
            )
            if op_inc is None:
                op_inc = context.pit_data.get_fundamental(
                    instrument_id=inst_id, metric="net_income", as_of=context.as_of
                )

            if op_inc is None or op_inc.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            cf = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="operating_cash_flow", as_of=context.as_of
            )
            cf_val = float(cf.value) if cf and cf.value is not None else float(op_inc.value) * 1.1

            assets = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="total_assets", as_of=context.as_of
            )
            denom_val = float(assets.value) if assets and assets.value is not None else 1.0

            if not validate_denominator(denom_val):
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INVALID_DENOMINATOR,
                )
                continue

            accrual = float(op_inc.value) - cf_val
            # Negative accruals (higher is better)
            score = -accrual / denom_val
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
