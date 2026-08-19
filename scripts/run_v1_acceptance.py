"""End-to-end acceptance run over the committed synthetic fixture.

Every stage runs for real - build, factor research, backtest, falsification, walk-forward
comparison, paper operations, research campaign - and the run happens in a temporary
workspace so it can never quietly overwrite the evidence artifacts in the repository.

The synthetic fixture is the target on purpose. It is small, committed, needs no network,
and carries the awkward cases deliberately: a delisting, a ticker change, a missing open,
a restated filing, a split, and a dividend. Passing here says the wiring holds end to end.
It says nothing about whether any strategy makes money.

    python scripts/run_v1_acceptance.py --config configs/releases/quantlab-v1.yaml
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from verify_release import sign  # noqa: E402

WALK_FORWARD = """walk_forward_id: acceptance-synthetic
split:
  window_type: expanding
  min_train_sessions: 12
  test_window_sessions: 6
  step_sessions: 6
  purge_sessions: 1
  embargo_sessions: 1
"""


def _prepare_workspace(workspace: Path) -> Path:
    for relative in ("configs", "migrations", "data/fixtures/synthetic_v1"):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO_ROOT / relative, target)
    (workspace / "configs" / "ml" / "acceptance-synthetic.yaml").write_text(
        WALK_FORWARD, encoding="utf-8"
    )
    return workspace


def run_acceptance(config_path: str, workspace: Path) -> tuple[int, dict[str, object]]:
    from quantlab.application.backtests import BacktestService
    from quantlab.application.dataset_service import DatasetService
    from quantlab.application.doctor import DoctorService
    from quantlab.application.factor_research import FactorResearchService
    from quantlab.application.models import ModelService
    from quantlab.application.paper import PaperService
    from quantlab.application.research import ResearchCampaignService
    from quantlab.application.validation import ValidationService

    with open(REPO_ROOT / config_path, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}

    dataset_id = str(cfg.get("target_dataset", "DATASET-v001"))
    strategy = str(cfg.get("strategy_config", "configs/strategies/synthetic-golden-v1.yaml"))
    start = date.fromisoformat(str(cfg.get("start_date", "2021-01-04")))
    end = date.fromisoformat(str(cfg.get("end_date", "2022-12-30")))

    print("=" * 70)
    print(f"QuantLab acceptance run: {cfg.get('release_id')} v{cfg.get('version')}")
    print(f"Workspace: {workspace}")
    print("=" * 70)

    doctor = DoctorService()
    doctor_report = doctor.run(offline=True)
    if doctor_report.overall_status == "FAIL":
        print("FAIL: environment checks did not pass", file=sys.stderr)
        return 1, {}
    print(f"  ok  environment ({doctor_report.overall_status})")

    manifest = DatasetService(base_dir=workspace).build_dataset(
        str(cfg.get("dataset_config", "configs/datasets/synthetic-v001.yaml")), offline=True
    )
    print(f"  ok  dataset built: {manifest.dataset_id} ({manifest.row_counts} rows)")

    factor = FactorResearchService(base_dir=workspace).run_factor_research(
        "momentum_12_1", dataset_id, start_date=start, end_date=end
    )
    print(
        f"  ok  factor research: {factor.num_sessions} rebalances, "
        f"rank IC {factor.rank_ic_mean:+.4f} (t={factor.rank_ic_tstat_newey_west:+.2f})"
    )

    backtest_service = BacktestService(base_dir=workspace)
    backtest = backtest_service.run_backtest(strategy, dataset_id, start, end)
    print(
        f"  ok  backtest: CAGR {backtest.metrics.cagr * 100:+.2f}%, "
        f"Sharpe {backtest.metrics.sharpe_ratio:+.2f}, {len(backtest.fills)} fills"
    )

    validation = ValidationService(base_dir=workspace).run_validation(
        config_path="configs/validation/default-v1.yaml",
        experiment_id="EXP-ACCEPTANCE",
        strategy_config_path=strategy,
        dataset_id=dataset_id,
        start_date=start,
        end_date=end,
        run_sweeps=True,
    )
    print(f"  ok  falsification: verdict {validation.verdict.value}")

    models = ModelService(base_dir=workspace).compare_models(
        dataset_id=dataset_id,
        walk_forward_config_path="configs/ml/acceptance-synthetic.yaml",
    )
    print(f"  ok  walk-forward comparison: champion {models.champion_model}")

    paper = PaperService(base_dir=workspace).simulate_forward(
        deployment_id="PAPER-SYNTHETIC",
        sessions_range="2022-01-03:2022-04-29",
    )
    print(f"  ok  paper operations: {paper.get('total_sessions', 0)} sessions simulated")

    campaign = ResearchCampaignService(base_dir=workspace).run_campaign(
        "configs/campaigns/quality-improves-momentum-v1.yaml"
    )
    print(f"  ok  research campaign: report {campaign.report_id}")

    record: dict[str, object] = {
        "release_id": cfg.get("release_id"),
        "version": cfg.get("version"),
        "dataset_id": manifest.dataset_id,
        "dataset_manifest_hash": manifest.manifest_hash,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "factor_rank_ic": round(factor.rank_ic_mean, 6),
        "backtest_cagr": round(float(backtest.metrics.cagr), 6),
        "backtest_sharpe": round(float(backtest.metrics.sharpe_ratio), 6),
        "backtest_content_hash": backtest.content_hash,
        "validation_verdict": validation.verdict.value,
        "ml_champion": models.champion_model,
        "paper_sessions": paper.get("total_sessions", 0),
        "campaign_report_id": campaign.report_id,
    }
    return 0, record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/releases/quantlab-v1.yaml")
    parser.add_argument(
        "--out",
        default="artifacts/golden/v1-acceptance/manifest.json",
        help="Where to write the acceptance record",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT))
    with tempfile.TemporaryDirectory() as tmp:
        workspace = _prepare_workspace(Path(tmp))
        code, record = run_acceptance(args.config, workspace)

    if code != 0:
        return code

    # Signed with the same function the verifier uses, so the two cannot drift into
    # disagreeing about which fields the signature covers.
    record["content_hash"] = sign(record)

    out_file = REPO_ROOT / args.out
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)

    print("=" * 70)
    print(f"Acceptance record written to {out_file.relative_to(REPO_ROOT)}")
    print(f"Content hash: {record['content_hash']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
