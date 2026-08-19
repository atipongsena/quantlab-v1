"""A session with no bar must carry a position at its last close, not at cost.

Repricing a held name to its purchase price for one session and back the next produces a
pair of double-digit daily returns that never happened. Volatility, Sharpe, drawdown, and
every bootstrap built on that series are then measuring a gap in the data.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.backtest.ledger import CashLedger, PositionLedger
from quantlab.backtest.marking import mark_to_market
from quantlab.domain.identity import InstrumentId

INSTRUMENT = InstrumentId(uuid.UUID(int=7))
AS_OF = datetime(2021, 6, 1, 21, 0, tzinfo=UTC)


def _ledgers() -> tuple[CashLedger, PositionLedger]:
    cash = CashLedger(initial_cash=Decimal("100000.00"))
    positions = PositionLedger()
    positions.apply_buy(INSTRUMENT, Decimal("100"), Decimal("50.00"))
    return cash, positions


def _value(close_prices: dict[InstrumentId, Decimal], carried: dict[InstrumentId, Decimal]):
    cash, positions = _ledgers()
    snapshot = mark_to_market(
        portfolio_id="PORT-TEST",
        as_of=AS_OF,
        cash_ledger=cash,
        position_ledger=positions,
        close_prices=close_prices,
        last_known_prices=carried,
    )
    return snapshot.positions[0].market_value


def test_missing_bar_uses_the_last_observed_close() -> None:
    # Bought at 50, last traded at 300, no bar today. Cost-basis fallback would value the
    # position at 5,000 instead of 30,000 - an 83% single-day loss from a data gap.
    value = _value({}, {INSTRUMENT: Decimal("300.00")})
    assert value == Decimal("30000.00")


def test_present_bar_wins_over_the_carried_price() -> None:
    value = _value({INSTRUMENT: Decimal("310.00")}, {INSTRUMENT: Decimal("300.00")})
    assert value == Decimal("31000.00")


def test_cost_basis_is_the_last_resort_only() -> None:
    # No bar and nothing observed yet: the position was bought today and has no close.
    value = _value({}, {})
    assert value == Decimal("5000.00")


def test_non_positive_price_is_treated_as_missing() -> None:
    value = _value({INSTRUMENT: Decimal("0.00")}, {INSTRUMENT: Decimal("300.00")})
    assert value == Decimal("30000.00")
