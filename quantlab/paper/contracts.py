"""Paper trading contracts, order representations, and broker account models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class PaperOrderStatus(StrEnum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaperOrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class BrokerAccount:
    account_id: str
    cash_balance: Decimal
    buying_power: Decimal
    positions: Mapping[InstrumentId, Decimal]

    def as_dict(self) -> dict[str, object]:
        return {
            "account_id": self.account_id,
            "cash_balance": str(self.cash_balance),
            "buying_power": str(self.buying_power),
            "positions": {str(k.value): str(v) for k, v in self.positions.items()},
        }


@dataclass(frozen=True, slots=True)
class PaperOrder:
    order_id: str
    session: date
    instrument_id: InstrumentId
    side: PaperOrderSide
    quantity: int
    order_type: str = "MARKET"
    status: PaperOrderStatus = PaperOrderStatus.PENDING

    def as_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "session": self.session.isoformat(),
            "instrument_id": str(self.instrument_id.value),
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class PaperFill:
    fill_id: str
    order_id: str
    instrument_id: InstrumentId
    side: PaperOrderSide
    quantity: int
    price: Decimal
    commission: Decimal
    filled_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "instrument_id": str(self.instrument_id.value),
            "side": self.side.value,
            "quantity": self.quantity,
            "price": str(self.price),
            "commission": str(self.commission),
            "filled_at": self.filled_at.isoformat(),
        }
