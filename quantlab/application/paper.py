"""Application service orchestrating daily paper trading lifecycle."""

from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.domain.identity import InstrumentId
from quantlab.paper.adapter import MockExecutionAdapter
from quantlab.paper.contracts import PaperOrder, PaperOrderSide


class PaperService:
    """Coordinates daily operational paper trading cycles and ledger synchronization."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._adapter = MockExecutionAdapter()

    def run_daily_cycle(
        self,
        session_date: date,
        strategy_config_path: str | Path = "configs/strategies/composite-top30-v1.yaml",
        dataset_id: str = "DATASET-v001",
        output_path: Path | None = None,
    ) -> dict[str, object]:
        # 1. Load strategy configuration
        cfg_file = Path(strategy_config_path)
        if not cfg_file.is_absolute():
            cfg_file = self._base_dir / cfg_file

        strat_cfg: dict[str, object] = {}
        if cfg_file.exists():
            with open(cfg_file, encoding="utf-8") as f:
                strat_cfg = yaml.safe_load(f) or {}

        # 2. Mock universe prices (30 synthetic instruments at $100 baseline)
        insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(30)]
        prices = {inst: Decimal("100.00") for inst in insts}
        self._adapter.set_prices(prices)

        # 3. Plan orders for Top 30 equal weight ($33,000 per name = 330 shares)
        orders_submitted: list[PaperOrder] = []
        fills_generated: list[dict[str, object]] = []

        target_qty = 330  # $33,000 notional at $100 price
        for i, inst in enumerate(insts):
            order = PaperOrder(
                order_id=f"ORD-{session_date.strftime('%Y%m%d')}-{i + 1:03d}",
                session=session_date,
                instrument_id=inst,
                side=PaperOrderSide.BUY,
                quantity=target_qty,
            )
            filled_ord, fills = self._adapter.submit_order(order)
            orders_submitted.append(filled_ord)
            for fill_item in fills:
                fills_generated.append(fill_item.as_dict())

        # 4. Mark to market
        account = self._adapter.get_account()
        positions = account.positions
        gross_equity = account.cash_balance + sum(
            qty * prices.get(inst, Decimal("100.00")) for inst, qty in positions.items()
        )

        result_payload = {
            "session": session_date.isoformat(),
            "strategy_id": str(strat_cfg.get("strategy_id", "composite-top30-v1")),
            "account_id": account.account_id,
            "orders_count": len(orders_submitted),
            "fills_count": len(fills_generated),
            "cash_balance": str(account.cash_balance),
            "total_equity": str(gross_equity),
            "positions_count": len(positions),
            "status": "COMPLETED",
        }

        # 5. Save paper run artifact
        out_file = output_path or self._base_dir / "artifacts" / "latest" / "paper-run.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2)

        return result_payload

    def reconcile_daily(
        self,
        session_date: date,
        strategy_config_path: str | Path = "configs/strategies/composite-top30-v1.yaml",
        output_path: Path | None = None,
    ) -> dict[str, object]:
        account = self._adapter.get_account()
        # In mock baseline, shadow matches broker
        from quantlab.paper.reconciliation import ShadowReconciler

        rep = ShadowReconciler.reconcile(
            shadow_cash=account.cash_balance,
            shadow_positions=account.positions,
            broker_account=account,
        )

        result_payload = rep.as_dict()
        result_payload["session"] = session_date.isoformat()

        out_file = (
            output_path or self._base_dir / "artifacts" / "latest" / "paper-reconciliation.json"
        )
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2)

        return result_payload
