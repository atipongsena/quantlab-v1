from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from quantlab.domain.market import MarketBar


@dataclass(frozen=True, slots=True)
class DataQualityCheck:
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QualityReport:
    dataset_id: str
    overall_status: str  # "PASS", "WARN", "FAIL"
    checks: tuple[DataQualityCheck, ...]
    confidence_score: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "overall_status": self.overall_status,
            "confidence_score": self.confidence_score,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


class DataQualityAuditor:
    def audit_market_bars(
        self,
        dataset_id: str,
        bars: Sequence[MarketBar],
        as_of: datetime | None = None,
    ) -> QualityReport:
        checks: list[DataQualityCheck] = []

        if not bars:
            checks.append(
                DataQualityCheck(
                    name="non_empty",
                    status="WARN",
                    message="Dataset is empty",
                )
            )
            return QualityReport(
                dataset_id=dataset_id,
                overall_status="WARN",
                checks=tuple(checks),
                confidence_score=0.5,
            )

        # 1. Price boundaries check
        invalid_prices = 0
        invalid_ohlc = 0
        future_timestamps = 0
        weekend_bars = 0

        by_inst: dict[object, list[MarketBar]] = {}
        for bar in bars:
            by_inst.setdefault(bar.instrument_id, []).append(bar)
            if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0 or bar.volume < 0:
                invalid_prices += 1
            if bar.high < max(bar.open, bar.low, bar.close) or bar.low > min(
                bar.open, bar.high, bar.close
            ):
                invalid_ohlc += 1
            if as_of is not None and bar.observed_at > as_of:
                future_timestamps += 1
            if bar.session.weekday() >= 5:
                weekend_bars += 1

        if invalid_prices == 0:
            checks.append(
                DataQualityCheck(
                    name="price_positivity",
                    status="PASS",
                    message="All prices are positive and volumes non-negative",
                )
            )
        else:
            checks.append(
                DataQualityCheck(
                    name="price_positivity",
                    status="FAIL",
                    message=f"Found {invalid_prices} non-positive prices or negative volumes",
                    details={"invalid_count": invalid_prices},
                )
            )

        if invalid_ohlc == 0:
            checks.append(
                DataQualityCheck(
                    name="ohlc_integrity",
                    status="PASS",
                    message="All high/low boundaries satisfy OHLC constraints",
                )
            )
        else:
            checks.append(
                DataQualityCheck(
                    name="ohlc_integrity",
                    status="FAIL",
                    message=f"Found {invalid_ohlc} bars violating high >= max and low <= min",
                    details={"invalid_count": invalid_ohlc},
                )
            )

        if future_timestamps == 0:
            checks.append(
                DataQualityCheck(
                    name="temporal_integrity",
                    status="PASS",
                    message="No future observations found ahead of as_of",
                )
            )
        else:
            checks.append(
                DataQualityCheck(
                    name="temporal_integrity",
                    status="FAIL",
                    message=f"Found {future_timestamps} bars observed in the future",
                    details={"future_count": future_timestamps},
                )
            )

        if weekend_bars == 0:
            checks.append(
                DataQualityCheck(
                    name="calendar_alignment",
                    status="PASS",
                    message="All sessions fall on standard business weekdays",
                )
            )
        else:
            checks.append(
                DataQualityCheck(
                    name="calendar_alignment",
                    status="FAIL",
                    message=f"Found {weekend_bars} bars recorded on weekends",
                    details={"weekend_count": weekend_bars},
                )
            )

        # 5. Chronological sequence check
        out_of_order = 0
        for inst_id, inst_bars in by_inst.items():
            for i in range(len(inst_bars) - 1):
                if inst_bars[i].session > inst_bars[i + 1].session:
                    out_of_order += 1
        if out_of_order == 0:
            checks.append(
                DataQualityCheck(
                    name="chronological_order",
                    status="PASS",
                    message="Bars are strictly chronological per instrument",
                )
            )
        else:
            checks.append(
                DataQualityCheck(
                    name="chronological_order",
                    status="FAIL",
                    message=f"Found {out_of_order} out-of-order sequence transitions",
                )
            )

        has_fail = any(c.status == "FAIL" for c in checks)
        has_warn = any(c.status == "WARN" for c in checks)
        overall_status = "FAIL" if has_fail else ("WARN" if has_warn else "PASS")

        passed_count = sum(1 for c in checks if c.status == "PASS")
        confidence_score = round(passed_count / len(checks), 2)

        return QualityReport(
            dataset_id=dataset_id,
            overall_status=overall_status,
            checks=tuple(checks),
            confidence_score=confidence_score,
        )
