import math
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


class Volatility60D(Factor):
    """60-day annualized realized volatility: std(daily_returns) * sqrt(252). Direction: -1."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="volatility_60d",
            name="60D Volatility",
            category=FactorCategory.RISK.value,
            description="60-session realized annualized price volatility",
            formula="std(returns[-60:]) * sqrt(252)",
            direction=-1,
            inputs=("prices",),
            lookback_sessions=60,
            availability_lag_sessions=0,
            missingness_policy="insufficient_history",
            price_semantic="total_return",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        start_date = context.session - timedelta(days=120)
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

            if len(valid_bars) < 61:  # Need 61 bars for 60 returns
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            recent_bars = valid_bars[-61:]
            closes = [float(b.close) for b in recent_bars]
            returns = [
                (closes[i] / closes[i - 1]) - 1.0
                for i in range(1, len(closes))
                if closes[i - 1] > 0
            ]

            if len(returns) < 60:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            mean_r = sum(returns) / len(returns)
            var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
            vol = math.sqrt(var_r) * math.sqrt(252.0)

            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=vol,
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


class MaxDrawdown252D(Factor):
    """252-session maximum peak-to-trough price drawdown. Direction: -1."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="max_drawdown_252d",
            name="252D Max Drawdown",
            category=FactorCategory.RISK.value,
            description="252-session maximum peak-to-trough price drawdown",
            formula="max_drawdown(prices[-252:])",
            direction=-1,
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
            valid_bars = [b for b in bars if b.session <= context.session]

            if len(valid_bars) < 252:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            recent_bars = valid_bars[-252:]
            closes = [float(b.close) for b in recent_bars]

            peak = closes[0]
            max_dd = 0.0
            for p in closes:
                if p > peak:
                    peak = p
                if peak > 0:
                    dd = (peak - p) / peak
                    if dd > max_dd:
                        max_dd = dd

            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=max_dd,
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


class Beta(Factor):
    """252-session rolling market beta vs equal-weight market return. Direction: -1."""

    def __init__(self, version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id="beta",
            name="Market Beta",
            category=FactorCategory.RISK.value,
            description="252-session market beta calculated against equal-weight market return",
            formula="cov(r_i, r_m) / var(r_m)",
            direction=-1,
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
        start_date = context.session - timedelta(days=450)
        end_date = context.session
        values: dict[InstrumentId, FactorValue] = {}

        # 1. Fetch bars for all instruments in universe to build market return series
        inst_returns: dict[InstrumentId, list[float]] = {}
        for inst_id in context.universe:
            bars = context.pit_data.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=context.as_of,
                adjusted=True,
            )
            valid_bars = [b for b in bars if b.session <= context.session]
            if len(valid_bars) >= 253:
                recent = valid_bars[-253:]
                closes = [float(b.close) for b in recent]
                r_series = [
                    (closes[i] / closes[i - 1]) - 1.0
                    for i in range(1, len(closes))
                    if closes[i - 1] > 0
                ]
                if len(r_series) >= 252:
                    inst_returns[inst_id] = r_series[-252:]

        # If market returns can't be computed or universe is too small
        if not inst_returns:
            for inst_id in context.universe:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
            return build_factor_snapshot(
                factor_id=self._def.factor_id,
                version=self._def.calculator_version,
                session=context.session,
                as_of=context.as_of,
                raw_values=values,
                universe=context.universe,
            )

        # 2. Equal-weight market return series for 252 sessions
        num_sessions = 252
        market_r = [
            sum(inst_returns[inst][t] for inst in inst_returns) / len(inst_returns)
            for t in range(num_sessions)
        ]

        mean_m = sum(market_r) / num_sessions
        var_m = sum((m - mean_m) ** 2 for m in market_r) / (num_sessions - 1)

        for inst_id in context.universe:
            if inst_id not in inst_returns:
                values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )
                continue

            r_i = inst_returns[inst_id]
            mean_i = sum(r_i) / num_sessions
            cov_im = sum(
                (r_i[t] - mean_i) * (market_r[t] - mean_m) for t in range(num_sessions)
            ) / (num_sessions - 1)

            beta_val = (cov_im / var_m) if var_m > 1e-12 else 1.0

            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=beta_val,
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
