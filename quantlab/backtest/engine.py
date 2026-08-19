"""Discrete event-driven simulation backtest engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal

from quantlab.analytics.performance import PerformanceCalculator
from quantlab.backtest.accounting import AccountingEngine
from quantlab.backtest.broker import SimulatedBroker
from quantlab.backtest.calendar import TradingCalendar
from quantlab.backtest.clock import HistoricalClock
from quantlab.backtest.costs import FeeModel, SlippageModel
from quantlab.backtest.events import (
    MarketCloseEvent,
    MarketOpenEvent,
    RebalanceDecisionEvent,
)
from quantlab.backtest.participation import VolumeParticipationModel
from quantlab.backtest.result import BacktestResult, BacktestSpec
from quantlab.domain.corporate_actions import CorporateAction
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import MarketBar
from quantlab.domain.orders import Fill, Order, OrderState
from quantlab.domain.portfolio import PortfolioSnapshot
from quantlab.factors.contracts import FactorSnapshot
from quantlab.portfolio.construction import ConstructionRequest, PortfolioConstructor
from quantlab.portfolio.orders import OrderPlanner, OrderPlanningSpec
from quantlab.portfolio.risk import RiskEngine


class BacktestEngine:
    """Authoritative event-driven backtest simulation engine."""

    def __init__(
        self,
        bars_provider: Callable[[date], Mapping[InstrumentId, MarketBar]],
        corporate_actions_provider: Callable[[date], Sequence[CorporateAction]] | None = None,
        alpha_provider: Callable[[date], FactorSnapshot] | None = None,
        sectors_provider: Callable[[date], Mapping[InstrumentId, str]] | None = None,
        universe_provider: Callable[[date], Sequence[InstrumentId]] | None = None,
        sessions_provider: Callable[[date, date], Sequence[date]] | None = None,
    ) -> None:
        self._bars_provider = bars_provider
        self._corporate_actions_provider = corporate_actions_provider or (lambda _: ())
        self._alpha_provider = alpha_provider
        self._sectors_provider = sectors_provider or (lambda _: {})
        self._universe_provider = universe_provider
        # A rule-based calendar approximates NYSE closures; the sessions actually present
        # in a dataset are the ground truth, including the ad-hoc closures (9/11, Sandy,
        # national days of mourning) no weekday-and-holiday rule reproduces. Callers with
        # a real dataset pass its calendar in.
        self._sessions_provider = sessions_provider or TradingCalendar.get_sessions

    def run(self, spec: BacktestSpec) -> BacktestResult:
        """Run simulation over specified date range according to spec."""
        all_sessions = list(self._sessions_provider(spec.start_session, spec.end_session))
        if not all_sessions:
            raise ValueError(
                f"No trading sessions in range {spec.start_session} to {spec.end_session}"
            )

        # Identify month-end rebalance sessions
        rebalance_sessions: list[date] = []
        for i, sess in enumerate(all_sessions):
            is_last_session = i == len(all_sessions) - 1
            if is_last_session or all_sessions[i + 1].month != sess.month:
                rebalance_sessions.append(sess)

        # Initialize accounting, broker, planner, and risk engine
        accounting = AccountingEngine(
            portfolio_id=f"PORT-{spec.strategy_id}", initial_cash=spec.initial_cash
        )
        broker = SimulatedBroker(
            slippage_model=SlippageModel(spec.slippage_bps),
            fee_model=FeeModel(spec.commission_per_share),
            participation_model=VolumeParticipationModel(spec.risk_spec.max_adv_participation),
        )
        planner = OrderPlanner(
            OrderPlanningSpec(
                no_trade_band_pct=spec.risk_spec.no_trade_band_pct,
                min_trade_dollar=spec.risk_spec.min_trade_dollar,
                max_adv_participation=spec.risk_spec.max_adv_participation,
            )
        )
        risk_engine = RiskEngine(spec.risk_spec)

        clock = HistoricalClock(
            sessions=all_sessions,
            rebalance_sessions=rebalance_sessions,
            strategy_id=spec.strategy_id,
        )

        all_orders: list[Order] = []
        all_fills: list[Fill] = []
        equity_series: dict[date, Decimal] = {}
        daily_returns: dict[date, float] = {}
        snapshots: dict[date, PortfolioSnapshot] = {}

        pending_orders: list[Order] = []
        # Last observed close per instrument, so a session with no bar for a held name
        # carries the position forward instead of repricing it to cost basis.
        last_known_prices: dict[InstrumentId, Decimal] = {}
        total_turnover = Decimal("0.0")
        total_fees = Decimal("0.0")
        total_slippage = Decimal("0.0")
        prev_equity = spec.initial_cash

        # Main discrete event simulation loop
        for event in clock.events():
            sess = event.session

            if isinstance(event, MarketOpenEvent):
                # 1. Apply any corporate actions before open
                actions = self._corporate_actions_provider(sess)
                for action in actions:
                    accounting.apply_corporate_action(action, effective_time=event.timestamp)

                # 2. Execute pending orders against market open
                bars = self._bars_provider(sess)
                remaining_pending: list[Order] = []

                for order in pending_orders:
                    bar = bars.get(order.instrument_id)
                    updated_order, fill = broker.execute_order(
                        order=order,
                        bar=bar,
                        session=sess,
                        fill_time=event.timestamp,
                    )
                    all_orders.append(updated_order)

                    if fill is not None:
                        all_fills.append(fill)
                        accounting.apply_fill(fill, order.side)
                        total_fees += fill.fees
                        ref_open = bar.open if bar else fill.price
                        slip = abs(fill.price - ref_open) * fill.quantity
                        total_slippage += slip

                    if updated_order.state == OrderState.SUBMITTED:
                        remaining_pending.append(updated_order)

                pending_orders = remaining_pending

            elif isinstance(event, MarketCloseEvent):
                # 3. Mark to market at session close
                bars = self._bars_provider(sess)
                close_prices = {inst: bar.close for inst, bar in bars.items()}
                snapshot = accounting.mark_to_market(
                    as_of=event.timestamp,
                    close_prices=close_prices,
                    last_known_prices=last_known_prices,
                )
                last_known_prices.update(close_prices)
                snapshots[sess] = snapshot

                tot_equity = snapshot.cash + sum(p.market_value for p in snapshot.positions)
                equity_series[sess] = tot_equity

                day_ret = (
                    float((tot_equity - prev_equity) / prev_equity)
                    if prev_equity > Decimal("0.0")
                    else 0.0
                )
                daily_returns[sess] = day_ret
                prev_equity = tot_equity

            elif isinstance(event, RebalanceDecisionEvent):
                # 4. Generate signals and plan orders for next session open
                if self._alpha_provider is not None:
                    alpha_snap = self._alpha_provider(sess)
                    universe = (
                        self._universe_provider(sess)
                        if self._universe_provider
                        else list(alpha_snap.valid_scores().keys())
                    )
                    curr_snap = snapshots.get(sess)
                    bars = self._bars_provider(sess)
                    close_prices = {inst: bar.close for inst, bar in bars.items()}
                    adv_shares = {inst: bar.volume for inst, bar in bars.items()}
                    sectors = self._sectors_provider(sess)

                    # Construct target portfolio
                    req = ConstructionRequest(
                        portfolio_id=accounting.portfolio_id,
                        decision_time=event.timestamp,
                        alpha_snapshot=alpha_snap,
                        universe=universe,
                        current_portfolio=curr_snap,
                        spec=spec.portfolio_spec,
                        market_prices=close_prices,
                    )
                    raw_target = PortfolioConstructor.construct(req)

                    # Risk engine verification
                    risk_dec = risk_engine.apply(raw_target, sectors=sectors)
                    approved_target = risk_dec.adjusted_target

                    # Order planning
                    tot_eq = equity_series.get(sess, spec.initial_cash)
                    plan = planner.plan(
                        current_portfolio=curr_snap,
                        approved_target=approved_target,
                        prices=close_prices,
                        total_equity=tot_eq,
                        adv_shares=adv_shares,
                    )
                    pending_orders.extend(plan.orders)
                    total_turnover += plan.turnover

        # Compute performance metrics
        metrics = PerformanceCalculator.calculate(
            equity_series=list(equity_series.values()),
            total_turnover=total_turnover,
            total_fees=total_fees,
            total_slippage=total_slippage,
        )

        return BacktestResult.create(
            spec=spec,
            equity_series=equity_series,
            daily_returns=daily_returns,
            portfolio_snapshots=snapshots,
            orders=tuple(all_orders),
            fills=tuple(all_fills),
            metrics=metrics,
        )
