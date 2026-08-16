"""Tests for portfolio concentration risk."""

import uuid
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.validation.concentration import ConcentrationAnalyzer


def test_concentration_analyzer_well_diversified() -> None:
    # 20 stocks equal weighted: each 5%
    weights = {InstrumentId(uuid.UUID(int=i)): Decimal("0.05") for i in range(1, 21)}
    sectors = {"Tech": Decimal("0.30"), "Health": Decimal("0.30"), "Finance": Decimal("0.40")}

    report = ConcentrationAnalyzer.evaluate(weights, sectors)
    assert not report.is_excessively_concentrated
    assert report.effective_number_of_bets == 20.0
    assert report.herfindahl_index == 0.05
