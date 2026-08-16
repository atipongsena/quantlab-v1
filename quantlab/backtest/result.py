"""Backtest specification and authoritative execution result contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from quantlab.analytics.performance import PerformanceMetrics
from quantlab.domain.orders import Fill, Order
from quantlab.domain.portfolio import PortfolioSnapshot
from quantlab.portfolio.construction import PortfolioSpec
from quantlab.portfolio.risk import RiskSpec


@dataclass(frozen=True, slots=True)
class BacktestSpec:
    """Configuration specification for a simulation run."""

    strategy_id: str
    dataset_id: str
    start_session: date
    end_session: date
    initial_cash: Decimal = Decimal("1000000.00")
    rebalance_frequency: str = "monthly"
    portfolio_spec: PortfolioSpec = field(default_factory=lambda: PortfolioSpec("default-spec"))
    risk_spec: RiskSpec = field(default_factory=RiskSpec)
    slippage_bps: Decimal = Decimal("5.0")
    commission_per_share: Decimal = Decimal("0.0")

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id,
            "dataset_id": self.dataset_id,
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "initial_cash": str(self.initial_cash),
            "rebalance_frequency": self.rebalance_frequency,
            "slippage_bps": str(self.slippage_bps),
            "commission_per_share": str(self.commission_per_share),
        }


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Authoritative result produced by BacktestEngine."""

    spec: BacktestSpec
    equity_series: Mapping[date, Decimal]
    daily_returns: Mapping[date, float]
    portfolio_snapshots: Mapping[date, PortfolioSnapshot]
    orders: tuple[Order, ...]
    fills: tuple[Fill, ...]
    metrics: PerformanceMetrics
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_id": self.spec.strategy_id,
            "dataset_id": self.spec.dataset_id,
            "start_session": self.spec.start_session.isoformat(),
            "end_session": self.spec.end_session.isoformat(),
            "initial_cash": str(self.spec.initial_cash),
            "ending_equity": str(list(self.equity_series.values())[-1])
            if self.equity_series
            else str(self.spec.initial_cash),
            "total_orders": len(self.orders),
            "total_fills": len(self.fills),
            "metrics": self.metrics.as_dict(),
            "content_hash": self.content_hash,
        }

    @classmethod
    def create(
        cls,
        spec: BacktestSpec,
        equity_series: Mapping[date, Decimal],
        daily_returns: Mapping[date, float],
        portfolio_snapshots: Mapping[date, PortfolioSnapshot],
        orders: tuple[Order, ...],
        fills: tuple[Fill, ...],
        metrics: PerformanceMetrics,
    ) -> BacktestResult:
        payload = {
            "spec": spec.as_dict(),
            "metrics": metrics.as_dict(),
            "equity": {d.isoformat(): str(eq) for d, eq in equity_series.items()},
            "order_count": len(orders),
            "fill_count": len(fills),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        chash = hashlib.sha256(encoded).hexdigest()

        return cls(
            spec=spec,
            equity_series=equity_series,
            daily_returns=daily_returns,
            portfolio_snapshots=portfolio_snapshots,
            orders=orders,
            fills=fills,
            metrics=metrics,
            content_hash=chash,
        )
