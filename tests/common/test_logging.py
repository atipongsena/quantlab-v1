from __future__ import annotations

from datetime import UTC, datetime

from quantlab.common.ids import DeterministicIdFactory
from quantlab.common.logging import build_log_event


def test_deterministic_id_factory_is_stable_and_namespaced() -> None:
    factory = DeterministicIdFactory()

    left = factory.from_parts("dataset", ("synthetic_v1", "2024-01-31"))
    right = factory.from_parts("dataset", ("synthetic_v1", "2024-01-31"))
    other_namespace = factory.from_parts("experiment", ("synthetic_v1", "2024-01-31"))

    assert left == right
    assert left != other_namespace


def test_structured_logs_include_correlation_domain_ids_and_redact_secrets() -> None:
    event = build_log_event(
        message="dataset published",
        occurred_at=datetime(2024, 1, 31, 22, 0, tzinfo=UTC),
        correlation_id="corr-1",
        domain_ids={"dataset_id": "dataset-1"},
        level="INFO",
        attributes={"api_key": "secret", "row_count": 42},
    )

    assert event.as_dict() == {
        "message": "dataset published",
        "occurred_at": "2024-01-31T22:00:00+00:00",
        "correlation_id": "corr-1",
        "domain_ids": {"dataset_id": "dataset-1"},
        "level": "INFO",
        "attributes": {"api_key": "***REDACTED***", "row_count": 42},
    }
