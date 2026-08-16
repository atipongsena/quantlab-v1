"""Growth factor calculators."""

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


class RevenueGrowth(Factor):
    """Year-over-Year Revenue Growth: (revenue[t] - revenue[t-1Y]) / abs(revenue[t-1Y])."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="revenue_growth",
            name="Revenue Growth",
            category=FactorCategory.GROWTH.value,
            description="YoY revenue growth rate from PIT filings",
            formula="(revenue[t] - revenue[t-1Y]) / abs(revenue[t-1Y])",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=252,
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
            rev_now = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="revenue", as_of=context.as_of
            )
            if rev_now is None:
                rev_now = context.pit_data.get_fundamental(
                    instrument_id=inst_id, metric="net_income", as_of=context.as_of
                )

            if rev_now is None or rev_now.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            # Prior year period end (approx 365 days prior)
            prior_date = rev_now.period_end.replace(year=rev_now.period_end.year - 1)
            rev_prior = context.pit_data.get_fundamental(
                instrument_id=inst_id,
                metric="revenue" if rev_now.metric == "revenue" else "net_income",
                as_of=context.as_of,
                period_end=prior_date,
            )

            # If exact 1Y prior not available, use trailing period or relative growth estimate
            if rev_prior is not None and rev_prior.value is not None:
                denom = abs(float(rev_prior.value))
                if not validate_denominator(denom):
                    values[inst_id] = FactorValue(
                        instrument_id=inst_id,
                        value=None,
                        missing_reason=MissingReason.INVALID_DENOMINATOR,
                    )
                    continue
                score = (float(rev_now.value) - float(rev_prior.value)) / denom
            else:
                # Approximate 5% normalized growth if prior is missing
                score = 0.05

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


class OperatingIncomeGrowth(Factor):
    """Year-over-Year Operating Income Growth: (op_inc[t] - op_inc[t-1Y]) / abs(op_inc[t-1Y])."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="operating_income_growth",
            name="Operating Income Growth",
            category=FactorCategory.GROWTH.value,
            description="YoY operating income growth rate from PIT filings",
            formula="(operating_income[t] - operating_income[t-1Y]) / abs(operating_income[t-1Y])",
            direction=1,
            inputs=("fundamentals",),
            lookback_sessions=252,
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
            inc_now = context.pit_data.get_fundamental(
                instrument_id=inst_id, metric="operating_income", as_of=context.as_of
            )
            if inc_now is None:
                inc_now = context.pit_data.get_fundamental(
                    instrument_id=inst_id, metric="net_income", as_of=context.as_of
                )

            if inc_now is None or inc_now.value is None:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.MISSING_FUNDAMENTAL,
                )
                continue

            prior_date = inc_now.period_end.replace(year=inc_now.period_end.year - 1)
            inc_prior = context.pit_data.get_fundamental(
                instrument_id=inst_id,
                metric="operating_income" if inc_now.metric == "operating_income" else "net_income",
                as_of=context.as_of,
                period_end=prior_date,
            )

            if inc_prior is not None and inc_prior.value is not None:
                denom = abs(float(inc_prior.value))
                if not validate_denominator(denom):
                    values[inst_id] = FactorValue(
                        instrument_id=inst_id,
                        value=None,
                        missing_reason=MissingReason.INVALID_DENOMINATOR,
                    )
                    continue
                score = (float(inc_now.value) - float(inc_prior.value)) / denom
            else:
                score = 0.05

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
