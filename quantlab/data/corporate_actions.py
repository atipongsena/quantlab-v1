from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.db import DatabaseEngine


class CorporateActionStore(Protocol):
    def record_action(self, action: CorporateAction) -> None: ...

    def get_actions(
        self,
        instrument_id: InstrumentId,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[CorporateAction, ...]: ...


class SqlCorporateActionStore:
    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._engine.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS corporate_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    effective_at TEXT NOT NULL,
                    announced_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    ratio TEXT,
                    cash_amount TEXT,
                    source TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_actions_inst 
                ON corporate_actions(instrument_id, effective_at);
                """
            )

    def record_action(self, action: CorporateAction) -> None:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO corporate_actions (
                    instrument_id, action_type, effective_at, announced_at,
                    available_at, ratio, cash_amount, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(action.instrument_id.value),
                    action.action_type.value,
                    action.effective_at.isoformat(),
                    action.announced_at.isoformat(),
                    action.available_at.isoformat(),
                    str(action.ratio) if action.ratio is not None else None,
                    str(action.cash_amount) if action.cash_amount is not None else None,
                    action.source,
                ),
            )

    def get_actions(
        self,
        instrument_id: InstrumentId,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[CorporateAction, ...]:
        query = "SELECT * FROM corporate_actions WHERE instrument_id = ?"
        params: list[object] = [str(instrument_id.value)]
        if start_date is not None:
            query += " AND effective_at >= ?"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND effective_at <= ?"
            params.append(end_date.isoformat())
        query += " ORDER BY effective_at ASC"

        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            actions = [
                CorporateAction(
                    instrument_id=instrument_id,
                    action_type=CorporateActionType(str(r["action_type"])),
                    effective_at=date.fromisoformat(str(r["effective_at"])),
                    announced_at=datetime.fromisoformat(str(r["announced_at"])).replace(tzinfo=UTC),
                    available_at=datetime.fromisoformat(str(r["available_at"])).replace(tzinfo=UTC),
                    ratio=Decimal(str(r["ratio"])) if r["ratio"] is not None else None,
                    cash_amount=Decimal(str(r["cash_amount"]))
                    if r["cash_amount"] is not None
                    else None,
                    source=str(r["source"]),
                )
                for r in rows
            ]
            return tuple(actions)


def compute_cumulative_adjustment_factors(
    bars: Sequence[MarketBar],
    actions: Sequence[CorporateAction],
    as_of: datetime | None = None,
) -> dict[date, tuple[Decimal, Decimal]]:
    """Compute cumulative backward adjustment factors for each bar session.

    Split ratio R multiplies past prices by 1/R and past volumes by R.
    Cash dividend D on effective_at multiplies past prices by (1 - D/P).
    """
    if not bars:
        return {}

    sorted_bars = sorted(bars, key=lambda b: b.session)

    # Filter actions by as_of availability
    valid_actions = [
        a
        for a in actions
        if (as_of is None or a.available_at <= as_of) and a.effective_at > sorted_bars[0].session
    ]

    # Compute factors for each action
    action_factors: list[tuple[date, Decimal, Decimal]] = []
    for a in valid_actions:
        eff = a.effective_at
        p_fac = Decimal("1")
        v_fac = Decimal("1")
        if a.action_type == CorporateActionType.SPLIT and a.ratio is not None:
            p_fac = Decimal("1") / a.ratio
            v_fac = a.ratio
        elif a.action_type == CorporateActionType.DIVIDEND and a.cash_amount is not None:
            prior_bars = [b for b in sorted_bars if b.session < eff]
            if prior_bars:
                prior_close = prior_bars[-1].close
                if prior_close > a.cash_amount:
                    p_fac = (prior_close - a.cash_amount) / prior_close
        action_factors.append((eff, p_fac, v_fac))

    cumulative_factors: dict[date, tuple[Decimal, Decimal]] = {}
    for bar in sorted_bars:
        p_acc = Decimal("1")
        v_acc = Decimal("1")
        for eff, p_fac, v_fac in action_factors:
            if bar.session < eff:
                p_acc *= p_fac
                v_acc *= v_fac
        cumulative_factors[bar.session] = (p_acc, v_acc)

    return cumulative_factors


def apply_adjustments(
    bars: Sequence[MarketBar],
    actions: Sequence[CorporateAction],
    as_of: datetime | None = None,
) -> tuple[MarketBar, ...]:
    """Return adjusted MarketBar instances computed point-in-time."""
    if not bars:
        return ()

    factors = compute_cumulative_adjustment_factors(bars, actions, as_of)
    adjusted_bars: list[MarketBar] = []

    for bar in sorted(bars, key=lambda b: b.session):
        p_fac, v_fac = factors.get(bar.session, (Decimal("1"), Decimal("1")))
        adj_open = (bar.open * p_fac).quantize(Decimal("0.000001"))
        adj_high = (bar.high * p_fac).quantize(Decimal("0.000001"))
        adj_low = (bar.low * p_fac).quantize(Decimal("0.000001"))
        adj_close = (bar.close * p_fac).quantize(Decimal("0.000001"))
        adj_vol = (bar.volume * v_fac).quantize(Decimal("0.0001"))

        # Safety clamp to guarantee high >= max(open, low, close) and low <= min(...)
        adj_high = max(adj_high, adj_open, adj_low, adj_close)
        adj_low = min(adj_low, adj_open, adj_high, adj_close)

        adjusted_bars.append(
            MarketBar(
                instrument_id=bar.instrument_id,
                session=bar.session,
                observed_at=bar.observed_at,
                open=adj_open,
                high=adj_high,
                low=adj_low,
                close=adj_close,
                volume=adj_vol,
                semantic=BarPriceSemantic.ADJUSTED,
                source=f"{bar.source}:adjusted",
            )
        )

    return tuple(adjusted_bars)
