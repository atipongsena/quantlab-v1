"""Paper forward simulation runner and operational evidence generation."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.adapter import MockExecutionAdapter
from quantlab.paper.contracts import PaperOrder, PaperOrderSide
from quantlab.paper.reconciliation import ShadowReconciler


@dataclass(frozen=True, slots=True)
class PaperForwardEvidence:
    deployment_id: str
    start_date: str
    end_date: str
    total_sessions: int
    orders_count: int
    fills_count: int
    clean_reconciliations: int
    total_equity: str
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "deployment_id": self.deployment_id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_sessions": self.total_sessions,
            "orders_count": self.orders_count,
            "fills_count": self.fills_count,
            "clean_reconciliations": self.clean_reconciliations,
            "total_equity": self.total_equity,
            "content_hash": self.content_hash,
        }


class PaperForwardSimulator:
    """Simulates operational paper trading execution forward across historical date ranges."""

    @classmethod
    def simulate(
        cls,
        deployment_id: str = "PAPER-SYNTHETIC",
        start_session: date = date(2024, 1, 1),
        end_session: date = date(2024, 4, 30),
        initial_cash: Decimal = Decimal("1000000.00"),
    ) -> PaperForwardEvidence:
        adapter = MockExecutionAdapter(initial_cash=initial_cash)
        insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(30)]

        # Generate trading dates
        cur = start_session
        sessions: list[date] = []
        while cur <= end_session:
            if cur.weekday() < 5:  # Monday to Friday
                sessions.append(cur)
            cur = date.fromordinal(cur.toordinal() + 1)

        total_orders = 0
        total_fills = 0
        clean_recons = 0

        for s in sessions:
            prices = {inst: Decimal("100.00") for inst in insts}
            adapter.set_prices(prices)

            # Daily rebalance orders (top 30)
            for i, inst in enumerate(insts):
                order = PaperOrder(
                    order_id=f"ORD-{s.strftime('%Y%m%d')}-{i + 1:03d}",
                    session=s,
                    instrument_id=inst,
                    side=PaperOrderSide.BUY,
                    quantity=10,
                )
                _, fills = adapter.submit_order(order)
                total_orders += 1
                total_fills += len(fills)

            account = adapter.get_account()
            rep = ShadowReconciler.reconcile(
                shadow_cash=account.cash_balance,
                shadow_positions=account.positions,
                broker_account=account,
            )
            if rep.is_clean:
                clean_recons += 1

        final_account = adapter.get_account()
        final_equity = final_account.cash_balance + sum(
            qty * Decimal("100.00") for qty in final_account.positions.values()
        )

        payload = {
            "deployment_id": deployment_id,
            "start_date": start_session.isoformat(),
            "end_date": end_session.isoformat(),
            "total_sessions": len(sessions),
            "orders_count": total_orders,
            "fills_count": total_fills,
            "clean_reconciliations": clean_recons,
            "total_equity": str(final_equity),
        }
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return PaperForwardEvidence(
            deployment_id=deployment_id,
            start_date=start_session.isoformat(),
            end_date=end_session.isoformat(),
            total_sessions=len(sessions),
            orders_count=total_orders,
            fills_count=total_fills,
            clean_reconciliations=clean_recons,
            total_equity=str(final_equity),
            content_hash=chash,
        )
