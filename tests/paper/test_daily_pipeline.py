"""Tests for daily paper execution lifecycle."""

from datetime import date
from pathlib import Path

from quantlab.application.paper import PaperService


def test_paper_service_daily_cycle(tmp_path: Path) -> None:
    service = PaperService(base_dir=tmp_path)
    out_file = tmp_path / "artifacts" / "latest" / "paper-run.json"

    res = service.run_daily_cycle(
        session_date=date(2026, 1, 5),
        output_path=out_file,
    )

    assert res["status"] == "COMPLETED"
    assert res["orders_count"] == 30
    assert res["fills_count"] == 30
    assert out_file.is_file()
