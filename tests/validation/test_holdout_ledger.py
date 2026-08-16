"""Tests for lockbox holdout ledger and consumption."""

from quantlab.validation.holdout import HoldoutService


def test_holdout_service_one_way_consumption() -> None:
    service = HoldoutService()
    candidate_id = "CAND-01"
    partition_id = "TEST-2024-2025"

    assert not service.is_consumed(candidate_id, partition_id)

    access1 = service.open_holdout(
        candidate_id=candidate_id,
        partition_id=partition_id,
        actor="researcher_1",
        purpose="Milestone M4 holdout evaluation",
    )

    assert service.is_consumed(candidate_id, partition_id)
    assert access1.candidate_id == candidate_id

    # Second open returns existing consumed record
    access2 = service.open_holdout(
        candidate_id=candidate_id,
        partition_id=partition_id,
        actor="researcher_2",
        purpose="Second attempt",
    )
    assert access1.access_id == access2.access_id
