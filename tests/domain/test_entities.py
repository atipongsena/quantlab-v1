from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.datasets import DatasetManifest, DatasetStatus
from quantlab.domain.identity import Instrument, InstrumentId, InstrumentStatus, InstrumentType
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.domain.signals import AlphaSnapshot, Signal, SignalDirection


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
