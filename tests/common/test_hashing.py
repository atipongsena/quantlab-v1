from __future__ import annotations

from decimal import Decimal

from quantlab.common.hashing import canonical_hash, canonicalize


def test_canonical_hash_is_independent_of_mapping_and_row_order() -> None:
    left = {
        "rows": [
            {"instrument_id": "b", "score": Decimal("0.2")},
            {"instrument_id": "a", "score": Decimal("0.1")},
        ],
        "meta": {"version": 1, "name": "fixture"},
    }
    right = {
        "meta": {"name": "fixture", "version": 1},
        "rows": [
            {"score": Decimal("0.1"), "instrument_id": "a"},
            {"score": Decimal("0.2"), "instrument_id": "b"},
        ],
    }

    assert canonical_hash(left) == canonical_hash(right)
    assert canonicalize(left) == canonicalize(right)


def test_canonical_hash_changes_when_value_changes() -> None:
    assert canonical_hash({"value": 1}) != canonical_hash({"value": 2})
