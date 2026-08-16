import inspect
import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorContext


def test_factor_context_has_no_label_fields() -> None:
    fields = [param.name for param in inspect.signature(FactorContext).parameters.values()]
    # Labels, forward returns, or future prices must not exist on FactorContext
    forbidden_terms = ["label", "forward", "future", "target", "lookahead"]
    for field_name in fields:
        for term in forbidden_terms:
            assert term not in field_name.lower(), f"Forbidden field on FactorContext: {field_name}"


def test_factor_context_attributes() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    # Creating context with minimal mocks
    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=None,  # type: ignore[arg-type]
        universe=[aapl],
    )

    assert not hasattr(context, "labels")
    assert not hasattr(context, "forward_returns")
