from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.datasets import DatasetManifest, DatasetStatus
from quantlab.domain.experiments import BacktestResult, Experiment, ExperimentStatus
from quantlab.domain.identity import Instrument, InstrumentId, InstrumentStatus, InstrumentType
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.domain.orders import Fill, Order, OrderSide, OrderState, OrderType
from quantlab.domain.paper import PaperDeployment, PaperDeploymentStatus
from quantlab.domain.portfolio import PortfolioSnapshot, Position, TargetPortfolio, TargetPosition
from quantlab.domain.signals import AlphaSnapshot, Signal, SignalDirection
from quantlab.domain.validation import ValidationResult, ValidationStatus


def test_market_bar_rejects_naive_timestamp() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000001"))

    with pytest.raises(ValueError, match="timezone-aware"):
        MarketBar(
            instrument_id=instrument_id,
            session=date(2024, 1, 2),
            observed_at=datetime(2024, 1, 2, 21, 0),
            open=Decimal("10.00"),
            high=Decimal("11.00"),
            low=Decimal("9.50"),
            close=Decimal("10.50"),
            volume=Decimal("1000"),
            semantic=BarPriceSemantic.RAW,
            source="fixture",
        )


def test_symbol_change_preserves_instrument_id() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000002"))
    first = Instrument(
        instrument_id=instrument_id,
        issuer_name="OldCo",
        security_name="OldCo Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NYSE",
        currency="USD",
        active_from=date(2020, 1, 1),
        status=InstrumentStatus.ACTIVE,
    )
    renamed = first.with_symbol_change(
        issuer_name="NewCo",
        security_name="NewCo Common Stock",
        exchange="NASDAQ",
    )

    assert renamed.instrument_id == instrument_id
    assert renamed.instrument_id == first.instrument_id
    assert renamed.issuer_name == "NewCo"
    assert first.issuer_name == "OldCo"


def test_money_rejects_float() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000003"))

    with pytest.raises(TypeError, match="Decimal"):
        MarketBar(
            instrument_id=instrument_id,
            session=date(2024, 1, 2),
            observed_at=datetime(2024, 1, 2, 21, 0, tzinfo=UTC),
            open=10.0,
            high=Decimal("11.00"),
            low=Decimal("9.50"),
            close=Decimal("10.50"),
            volume=Decimal("1000"),
            semantic=BarPriceSemantic.RAW,
            source="fixture",
        )


def test_entities_are_immutable_and_value_equal() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000004"))
    left = Signal(
        instrument_id=instrument_id,
        decision_time=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
        direction=SignalDirection.LONG,
        score=Decimal("0.42"),
        model_id="baseline",
        source_dataset_id="dataset-1",
    )
    right = Signal(
        instrument_id=instrument_id,
        decision_time=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
        direction=SignalDirection.LONG,
        score=Decimal("0.42"),
        model_id="baseline",
        source_dataset_id="dataset-1",
    )

    assert left == right
    with pytest.raises(FrozenInstanceError):
        left.model_id = "mutated"  # type: ignore[misc]


def test_invalid_boundary_cases_are_rejected() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000005"))

    with pytest.raises(ValueError, match="active_to"):
        Instrument(
            instrument_id=instrument_id,
            issuer_name="BoundaryCo",
            security_name="BoundaryCo Common Stock",
            instrument_type=InstrumentType.EQUITY,
            exchange="NYSE",
            currency="USD",
            active_from=date(2024, 1, 2),
            active_to=date(2024, 1, 1),
            status=InstrumentStatus.DELISTED,
        )

    with pytest.raises(TypeError, match="date without time"):
        MarketBar(
            instrument_id=instrument_id,
            session=datetime(2024, 1, 2, tzinfo=UTC),
            observed_at=datetime(2024, 1, 2, 21, 0, tzinfo=UTC),
            open=Decimal("10.00"),
            high=Decimal("11.00"),
            low=Decimal("9.50"),
            close=Decimal("10.50"),
            volume=Decimal("1000"),
            semantic=BarPriceSemantic.RAW,
            source="fixture",
        )

    with pytest.raises(ValueError, match="positive"):
        CorporateAction(
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=date(2024, 6, 1),
            announced_at=datetime(2024, 5, 1, 12, 0, tzinfo=UTC),
            available_at=datetime(2024, 5, 1, 13, 0, tzinfo=UTC),
            ratio=Decimal("0"),
            cash_amount=None,
            source="fixture",
        )

    with pytest.raises(ValueError, match="signals"):
        AlphaSnapshot(
            snapshot_id="empty",
            decision_time=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
            signals=(),
            source_dataset_id="dataset-1",
        )

    with pytest.raises(ValueError, match="content_hash"):
        DatasetManifest(
            dataset_id="dataset-1",
            status=DatasetStatus.PUBLISHED,
            created_at=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
            as_of=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
            source="fixture",
            content_hash="",
            row_count=1,
        )


def test_order_state_transition_table() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000006"))
    created = Order(
        order_id="order-1",
        instrument_id=instrument_id,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10"),
        state=OrderState.CREATED,
        created_at=datetime(2024, 1, 31, 22, 1, tzinfo=UTC),
    )

    submitted = created.transition_to(
        OrderState.SUBMITTED,
        transitioned_at=datetime(2024, 1, 31, 22, 2, tzinfo=UTC),
    )
    partially_filled = submitted.transition_to(
        OrderState.PARTIALLY_FILLED,
        transitioned_at=datetime(2024, 1, 31, 22, 3, tzinfo=UTC),
    )
    filled = partially_filled.transition_to(
        OrderState.FILLED,
        transitioned_at=datetime(2024, 1, 31, 22, 4, tzinfo=UTC),
    )

    assert submitted.state is OrderState.SUBMITTED
    assert partially_filled.state is OrderState.PARTIALLY_FILLED
    assert filled.state is OrderState.FILLED
    assert created.state is OrderState.CREATED

    with pytest.raises(ValueError, match="illegal order state transition"):
        created.transition_to(
            OrderState.FILLED,
            transitioned_at=datetime(2024, 1, 31, 22, 5, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="terminal"):
        filled.transition_to(
            OrderState.CANCELLED,
            transitioned_at=datetime(2024, 1, 31, 22, 5, tzinfo=UTC),
        )


def test_remaining_contracts_are_immutable_and_validate_boundaries() -> None:
    instrument_id = InstrumentId.from_uuid(UUID("00000000-0000-0000-0000-000000000007"))
    target = TargetPosition(
        instrument_id=instrument_id,
        target_weight=Decimal("0.25"),
        target_quantity=Decimal("12"),
    )
    target_portfolio = TargetPortfolio(
        portfolio_id="target-1",
        decision_time=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
        positions=(target,),
        source_alpha_snapshot_id="alpha-1",
    )
    fill = Fill(
        fill_id="fill-1",
        order_id="order-1",
        instrument_id=instrument_id,
        filled_at=datetime(2024, 2, 1, 14, 30, tzinfo=UTC),
        quantity=Decimal("12"),
        price=Decimal("10.50"),
        fees=Decimal("0.25"),
        source="fixture",
    )
    position = Position(
        instrument_id=instrument_id,
        quantity=Decimal("12"),
        cost_basis=Decimal("126.00"),
        market_value=Decimal("130.00"),
    )
    snapshot = PortfolioSnapshot(
        portfolio_id="portfolio-1",
        as_of=datetime(2024, 2, 1, 21, 0, tzinfo=UTC),
        cash=Decimal("1000.00"),
        positions=(position,),
    )
    experiment = Experiment(
        experiment_id="experiment-1",
        status=ExperimentStatus.LOCKED,
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        config_hash="abc123",
        dataset_id="dataset-1",
    )
    backtest = BacktestResult(
        result_id="backtest-1",
        experiment_id=experiment.experiment_id,
        created_at=datetime(2024, 2, 2, 12, 0, tzinfo=UTC),
        equity_curve_hash="curve123",
        annual_return=Decimal("0.10"),
        max_drawdown=Decimal("-0.12"),
    )
    validation = ValidationResult(
        validation_id="validation-1",
        status=ValidationStatus.PASS,
        created_at=datetime(2024, 2, 2, 13, 0, tzinfo=UTC),
        subject_id=backtest.result_id,
        summary="lockbox passed",
    )
    deployment = PaperDeployment(
        deployment_id="paper-1",
        status=PaperDeploymentStatus.READY,
        created_at=datetime(2024, 2, 2, 14, 0, tzinfo=UTC),
        experiment_id=experiment.experiment_id,
        broker_account_ref="paper-account",
    )

    assert target_portfolio.positions == (target,)
    assert snapshot.positions == (position,)
    assert fill.price == Decimal("10.50")
    assert validation.subject_id == "backtest-1"
    assert deployment.experiment_id == "experiment-1"

    with pytest.raises(FrozenInstanceError):
        target.target_weight = Decimal("0.30")  # type: ignore[misc]

    with pytest.raises(TypeError, match="Decimal"):
        TargetPosition(
            instrument_id=instrument_id,
            target_weight=0.25,
            target_quantity=None,
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        PaperDeployment(
            deployment_id="paper-2",
            status=PaperDeploymentStatus.READY,
            created_at=datetime(2024, 2, 2, 14, 0),
            experiment_id=experiment.experiment_id,
            broker_account_ref="paper-account",
        )
