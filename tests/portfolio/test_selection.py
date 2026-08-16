"""Tests for portfolio asset selection and buffer hysteresis."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.portfolio.selection import SelectionReason, TopKBufferSelector


def test_top_k_selection_initial_entry() -> None:
    # 50 instruments with scores 50.0 down to 1.0
    instruments = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(50)]
    scores = {inst: float(50 - i) for i, inst in enumerate(instruments)}

    selector = TopKBufferSelector(target_size=30, buffer_size=40)
    selected = selector.select(scores, current_holdings=())

    assert len(selected) == 30
    # Top 30 should all be selected as TOP_K_ENTRY
    for item in selected:
        assert item.reason == SelectionReason.TOP_K_ENTRY
        assert item.rank <= 30


def test_buffer_hold_retains_existing_holding_in_buffer_zone() -> None:
    instruments = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(50)]
    scores = {inst: float(50 - i) for i, inst in enumerate(instruments)}

    # Existing holding ranked #35 (in buffer 31..40)
    holding_35 = instruments[34]

    selector = TopKBufferSelector(target_size=30, buffer_size=40)
    selected = selector.select(scores, current_holdings=(holding_35,))

    assert len(selected) == 30
    selected_insts = {s.instrument_id: s for s in selected}

    # Holding 35 must be retained with reason BUFFER_HOLD
    assert holding_35 in selected_insts
    assert selected_insts[holding_35].reason == SelectionReason.BUFFER_HOLD
    assert selected_insts[holding_35].rank == 35

    # Exactly 29 new/top entries selected
    top_entries = [s for s in selected if s.reason == SelectionReason.TOP_K_ENTRY]
    assert len(top_entries) == 29


def test_buffer_exits_holding_outside_buffer() -> None:
    instruments = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(50)]
    scores = {inst: float(50 - i) for i, inst in enumerate(instruments)}

    # Existing holding ranked #45 (outside buffer 40)
    holding_45 = instruments[44]

    selector = TopKBufferSelector(target_size=30, buffer_size=40)
    selected = selector.select(scores, current_holdings=(holding_45,))

    assert len(selected) == 30
    selected_insts = {s.instrument_id for s in selected}
    assert holding_45 not in selected_insts


def test_deterministic_order_invariance() -> None:
    instruments = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(50)]
    scores = {inst: float(50 - i) for i, inst in enumerate(instruments)}

    selector = TopKBufferSelector(target_size=30, buffer_size=40)

    # Permute dictionary insertion order
    permuted_scores = {k: scores[k] for k in reversed(list(scores.keys()))}
    selected1 = selector.select(scores)
    selected2 = selector.select(permuted_scores)

    assert [s.instrument_id for s in selected1] == [s.instrument_id for s in selected2]
