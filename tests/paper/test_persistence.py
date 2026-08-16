"""Tests for SQLite paper state persistence."""

import uuid
from decimal import Decimal
from pathlib import Path

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import BrokerAccount
from quantlab.paper.persistence import PaperStateStore


def test_paper_state_store_save_and_load(tmp_path: Path) -> None:
    db_file = tmp_path / "paper.db"
    store = PaperStateStore(db_file)

    inst1 = InstrumentId(uuid.UUID(int=1))
    account = BrokerAccount(
        account_id="PAPER-001",
        cash_balance=Decimal("250000.00"),
        buying_power=Decimal("250000.00"),
        positions={inst1: Decimal("150")},
    )

    store.save_account(account)
    loaded = store.load_account("PAPER-001")

    assert loaded is not None
    assert loaded.account_id == "PAPER-001"
    assert loaded.cash_balance == Decimal("250000.00")
    assert loaded.positions[inst1] == Decimal("150")
