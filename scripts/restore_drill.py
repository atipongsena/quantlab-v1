"""Recovery drill: rebuild paper account state from the fill ledger on disk.

The paper broker keeps a live account, and it also appends every fill to SQLite. The
claim being tested is that the second is sufficient: lose the account row entirely and
the exact cash balance and share holdings can still be reconstructed by replaying fills.

The drill writes a multi-leg sequence - buys, a partial exit, a full exit, commissions on
every leg - tracks the expected state independently as it goes, then throws the live
account away, **reopens the database**, reads the fills back out, and replays them. Going
back through storage is the point: replaying fill objects still held in memory would
verify the arithmetic while saying nothing about whether the ledger was durable.

    python scripts/restore_drill.py
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import BrokerAccount, PaperFill, PaperOrderSide
from quantlab.paper.persistence import PaperStateStore
from quantlab.paper.recovery import DisasterRecoveryEngine

REPO_ROOT = Path(__file__).resolve().parent.parent
INITIAL_CASH = Decimal("1000000.00")
ACCOUNT_ID = "DRILL-ACCOUNT"

# (instrument index, side, quantity, price, commission)
LEGS: tuple[tuple[int, PaperOrderSide, int, str, str], ...] = (
    (1, PaperOrderSide.BUY, 100, "150.00", "1.50"),
    (2, PaperOrderSide.BUY, 250, "88.40", "2.50"),
    (3, PaperOrderSide.BUY, 40, "612.75", "0.40"),
    (1, PaperOrderSide.BUY, 50, "155.25", "0.75"),
    (2, PaperOrderSide.SELL, 100, "91.10", "1.00"),
    (3, PaperOrderSide.SELL, 40, "640.00", "0.40"),
    (1, PaperOrderSide.SELL, 25, "161.80", "0.25"),
)


def _build_fills() -> list[PaperFill]:
    fills: list[PaperFill] = []
    for index, (instrument_index, side, quantity, price, commission) in enumerate(LEGS):
        fills.append(
            PaperFill(
                fill_id=f"DRILL-FILL-{index:03d}",
                order_id=f"DRILL-ORD-{index:03d}",
                instrument_id=InstrumentId(uuid.UUID(int=instrument_index)),
                side=side,
                quantity=quantity,
                price=Decimal(price),
                commission=Decimal(commission),
                filled_at=datetime(2026, 1, 5, 14, 30, tzinfo=UTC) + timedelta(minutes=index),
            )
        )
    return fills


def _expected_state(fills: Sequence[PaperFill]) -> tuple[Decimal, dict[InstrumentId, Decimal]]:
    """Track the live account independently of the recovery engine."""
    cash = INITIAL_CASH
    positions: dict[InstrumentId, Decimal] = {}
    for fill in fills:
        notional = fill.price * Decimal(fill.quantity)
        held = positions.get(fill.instrument_id, Decimal("0"))
        if fill.side == PaperOrderSide.BUY:
            cash -= notional + fill.commission
            positions[fill.instrument_id] = held + Decimal(fill.quantity)
        else:
            cash += notional - fill.commission
            remaining = held - Decimal(fill.quantity)
            if remaining <= 0:
                positions.pop(fill.instrument_id, None)
            else:
                positions[fill.instrument_id] = remaining
    return cash, positions


def run_restore_drill(db_path: Path) -> int:
    if db_path.exists():
        db_path.unlink()

    print("=" * 70)
    print("Paper recovery drill: reconstruct account state from the fill ledger")
    print("=" * 70)

    fills = _build_fills()
    store = PaperStateStore(db_path)
    for fill in fills:
        store.record_fill(fill)

    expected_cash, expected_positions = _expected_state(fills)
    live = BrokerAccount(
        account_id=ACCOUNT_ID,
        cash_balance=expected_cash,
        buying_power=expected_cash,
        positions=expected_positions,
    )
    store.save_account(live)
    print(
        f"  recorded {len(fills)} fills across {len({f.instrument_id for f in fills})} instruments"
    )
    print(f"  live account: cash {live.cash_balance}, {len(live.positions)} open positions")

    # Simulate the crash: drop every reference to the live account and reopen the store
    # from disk, exactly as a restarted process would.
    del live, store
    reopened = PaperStateStore(db_path)
    replayed = reopened.load_fills()
    print(f"  reopened database and read back {len(replayed)} fills")

    if len(replayed) != len(fills):
        print(
            f"FAIL: ledger held {len(replayed)} fills, expected {len(fills)}",
            file=sys.stderr,
        )
        return 1

    recovered = DisasterRecoveryEngine.reconstruct_from_fills(
        account_id=ACCOUNT_ID,
        initial_cash=INITIAL_CASH,
        fills=replayed,
    )

    failures: list[str] = []
    if recovered.cash_balance != expected_cash:
        failures.append(f"cash {recovered.cash_balance} != expected {expected_cash}")
    if recovered.positions != expected_positions:
        failures.append(f"positions {dict(recovered.positions)} != expected {expected_positions}")

    print("-" * 70)
    print(f"  expected cash    : {expected_cash}")
    print(f"  reconstructed    : {recovered.cash_balance}")
    for instrument, quantity in sorted(recovered.positions.items(), key=lambda i: str(i[0].value)):
        print(f"  position         : {instrument.value} -> {quantity} shares")
    print("-" * 70)

    db_path.unlink(missing_ok=True)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("PASS: account state reconstructed exactly from the persisted fill ledger")
    print("=" * 70)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=str(REPO_ROOT / "data" / "drill_recovery.db"),
        help="Where to write the throwaway drill database",
    )
    args = parser.parse_args(argv)
    return run_restore_drill(Path(args.db))


if __name__ == "__main__":
    raise SystemExit(main())
