"""Deterministic portfolio construction engine combining selection and weighting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.portfolio import PortfolioSnapshot, TargetPortfolio, TargetPosition
from quantlab.factors.contracts import FactorSnapshot
from quantlab.portfolio.selection import TopKBufferSelector
from quantlab.portfolio.weighting import EqualWeighting, InverseVolatilityWeighting, WeightingScheme


@dataclass(frozen=True, slots=True)
class PortfolioSpec:
    """Configuration specification for portfolio construction."""

    strategy_id: str
    target_size: int = 30
    buffer_size: int = 40
    weighting_method: str = "equal"
    cash_buffer_pct: Decimal = Decimal("0.01")
    max_name_weight: Decimal = Decimal("0.05")
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConstructionRequest:
    """Input payload for portfolio construction."""

    portfolio_id: str
    decision_time: datetime
    alpha_snapshot: FactorSnapshot
    universe: Sequence[InstrumentId]
    current_portfolio: PortfolioSnapshot | None = None
    spec: PortfolioSpec = field(default_factory=lambda: PortfolioSpec("default-top30"))
    market_prices: Mapping[InstrumentId, Decimal] | None = None
    risk_metrics: Mapping[InstrumentId, float] | None = None


class PortfolioConstructor:
    """Constructs auditable target portfolios from alpha signals and universe state."""

    @classmethod
    def construct(cls, request: ConstructionRequest) -> TargetPortfolio:
        spec = request.spec
        valid_scores = request.alpha_snapshot.valid_scores()

        # Filter scores by tradable universe
        universe_set = set(request.universe)
        eligible_scores = {
            inst: score for inst, score in valid_scores.items() if inst in universe_set
        }

        # Determine current active holdings
        current_holdings: list[InstrumentId] = []
        if request.current_portfolio is not None:
            current_holdings = [
                pos.instrument_id
                for pos in request.current_portfolio.positions
                if pos.quantity > Decimal("0.0")
            ]

        # 1. Selection via Top-K + Buffer policy
        selector = TopKBufferSelector(
            target_size=spec.target_size,
            buffer_size=spec.buffer_size,
        )
        selected_assets = selector.select(
            scores=eligible_scores,
            current_holdings=current_holdings,
        )

        if not selected_assets:
            return TargetPortfolio(
                portfolio_id=request.portfolio_id,
                decision_time=request.decision_time,
                positions=(),
                source_alpha_snapshot_id=request.alpha_snapshot.content_hash,
            )

        # 2. Weighting
        gross_exposure = (Decimal("1.0") - spec.cash_buffer_pct).quantize(Decimal("0.000001"))
        weighting_scheme: WeightingScheme
        if spec.weighting_method == "inverse_volatility":
            weighting_scheme = InverseVolatilityWeighting()
        else:
            weighting_scheme = EqualWeighting()

        raw_weights = weighting_scheme.compute_weights(
            selected_assets=selected_assets,
            total_target_weight=gross_exposure,
            risk_metrics=request.risk_metrics,
        )

        # 3. Build target positions (deterministic order by instrument UUID string)
        target_positions: list[TargetPosition] = []
        sorted_instruments = sorted(raw_weights.keys(), key=lambda inst: str(inst.value))

        for inst in sorted_instruments:
            weight = raw_weights[inst]
            # Enforce max name cap if configured
            if spec.max_name_weight and weight > spec.max_name_weight:
                weight = spec.max_name_weight

            target_positions.append(
                TargetPosition(
                    instrument_id=inst,
                    target_weight=weight,
                    target_quantity=None,
                )
            )

        return TargetPortfolio(
            portfolio_id=request.portfolio_id,
            decision_time=request.decision_time,
            positions=tuple(target_positions),
            source_alpha_snapshot_id=request.alpha_snapshot.content_hash,
        )
