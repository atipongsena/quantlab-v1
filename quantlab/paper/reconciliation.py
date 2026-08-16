"""Shadow position and cash reconciliation engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.breaks import BreakSeverity, BreakType, TradeBreak
from quantlab.paper.contracts import BrokerAccount


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    as_of: datetime
    is_clean: bool
    breaks: tuple[TradeBreak, ...]
    max_severity: BreakSeverity
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "is_clean": self.is_clean,
            "breaks": [b.as_dict() for b in self.breaks],
            "max_severity": self.max_severity.value,
            "content_hash": self.content_hash,
        }


class ShadowReconciler:
    """Reconciles internal accounting state with external broker records."""

    @classmethod
    def reconcile(
        cls,
        shadow_cash: Decimal,
        shadow_positions: Mapping[InstrumentId, Decimal],
        broker_account: BrokerAccount,
        cash_tolerance: Decimal = Decimal("1.00"),
        as_of: datetime | None = None,
    ) -> ReconciliationReport:
        now = as_of or datetime.now(tz=UTC)
        breaks: list[TradeBreak] = []

        # 1. Cash reconciliation
        cash_diff = abs(shadow_cash - broker_account.cash_balance)
        if cash_diff > cash_tolerance:
            severity = (
                BreakSeverity.CRITICAL if cash_diff > Decimal("100.00") else BreakSeverity.WARNING
            )
            breaks.append(
                TradeBreak(
                    break_type=BreakType.CASH_MISMATCH,
                    instrument_id=None,
                    shadow_value=shadow_cash,
                    broker_value=broker_account.cash_balance,
                    difference=cash_diff,
                    severity=severity,
                    reason=(
                        f"Cash balance mismatch exceeds tolerance: shadow ${shadow_cash}, "
                        f"broker ${broker_account.cash_balance}"
                    ),
                )
            )

        # 2. Position reconciliation
        all_insts = sorted(
            set(shadow_positions.keys()) | set(broker_account.positions.keys()),
            key=lambda x: str(x.value),
        )

        for inst in all_insts:
            s_qty = shadow_positions.get(inst, Decimal("0"))
            b_qty = broker_account.positions.get(inst, Decimal("0"))
            qty_diff = abs(s_qty - b_qty)

            if qty_diff > 0:
                if s_qty == 0:
                    b_type = BreakType.UNEXPECTED_POSITION
                elif b_qty == 0:
                    b_type = BreakType.MISSING_POSITION
                else:
                    b_type = BreakType.POSITION_QUANTITY_MISMATCH

                breaks.append(
                    TradeBreak(
                        break_type=b_type,
                        instrument_id=inst,
                        shadow_value=s_qty,
                        broker_value=b_qty,
                        difference=qty_diff,
                        severity=BreakSeverity.CRITICAL,
                        reason=(
                            f"Position share mismatch for {inst.value}: shadow {s_qty}, "
                            f"broker {b_qty}"
                        ),
                    )
                )

        is_clean = len(breaks) == 0
        if not breaks:
            max_sev = BreakSeverity.NONE
        elif any(b.severity == BreakSeverity.CRITICAL for b in breaks):
            max_sev = BreakSeverity.CRITICAL
        else:
            max_sev = BreakSeverity.WARNING

        payload = {
            "as_of": now.isoformat(),
            "is_clean": is_clean,
            "breaks": [b.as_dict() for b in breaks],
            "max_severity": max_sev.value,
        }
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return ReconciliationReport(
            as_of=now,
            is_clean=is_clean,
            breaks=tuple(breaks),
            max_severity=max_sev,
            content_hash=chash,
        )
