"""Application service for model comparison and walk-forward workflows."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.application.factor_research import FactorResearchService
from quantlab.ml.contracts import MLDataset, MLFeatureRow
from quantlab.ml.runner import ModelComparisonResult, ModelComparisonRunner
from quantlab.ml.splits import WalkForwardSpec, WindowType
from quantlab.ml.walk_forward import PurgedWalkForwardCV

DEFAULT_FEATURES = (
    "momentum_12_1",
    "momentum_6_1",
    "volatility_60d",
    "max_drawdown_252d",
)


@dataclass(frozen=True, slots=True)
class ShuffleVerdict:
    """Where a model's real score falls in the distribution of shuffled-label scores."""

    model_name: str
    observed_rank_ic: float
    null_mean: float
    null_max: float
    permutations: int
    p_value: float

    @property
    def survives(self) -> bool:
        """True when the real score is not comfortably reproducible by chance.

        The threshold is deliberately loose. This control is not there to certify a
        model as good; it is there to catch a pipeline whose measured skill is
        indistinguishable from what shuffled labels produce.
        """
        return self.p_value <= 0.2

    def as_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "observed_rank_ic": round(self.observed_rank_ic, 4),
            "null_mean": round(self.null_mean, 4),
            "null_max": round(self.null_max, 4),
            "permutations": self.permutations,
            "p_value": round(self.p_value, 4),
            "survives": self.survives,
        }


@dataclass(frozen=True, slots=True)
class LabelShuffleControl:
    """Result of the label-shuffle permutation test."""

    real: ModelComparisonResult
    permuted: tuple[ModelComparisonResult, ...]
    verdicts: tuple[ShuffleVerdict, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "permutations": len(self.permuted),
            "verdicts": [v.as_dict() for v in self.verdicts],
        }


class ModelService:
    """Coordinates walk-forward panel construction, model comparison, and artifacts."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._research = FactorResearchService(self._base_dir)
        # Building the panel means computing every factor at every rebalance, which is
        # the expensive part. The comparison and its label-shuffle control run on the
        # same panel, so it is built once per process.
        self._panel_cache: dict[tuple[object, ...], MLDataset] = {}

    def _panel(
        self,
        dataset_id: str,
        start_date: date | None,
        end_date: date | None,
        label_horizon: int,
    ) -> MLDataset:
        key = (dataset_id, start_date, end_date, label_horizon)
        cached = self._panel_cache.get(key)
        if cached is not None:
            return cached

        panel = self._research.build_factor_panel(
            dataset_id=dataset_id,
            factor_ids=DEFAULT_FEATURES,
            start_date=start_date,
            end_date=end_date,
            label_horizon=label_horizon,
        )
        self._panel_cache[key] = panel
        return panel

    def _load_walk_forward_spec(self, config_path: str | Path) -> WalkForwardSpec:
        path = Path(config_path)
        if not path.is_absolute():
            path = self._base_dir / path
        if not path.exists():
            return WalkForwardSpec(
                window_type=WindowType.EXPANDING,
                min_train_sessions=60,
                test_window_sessions=12,
                step_sessions=12,
                purge_sessions=1,
                embargo_sessions=1,
            )

        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        cfg = raw.get("split", raw)

        window = str(cfg.get("window_type", "expanding")).lower()
        return WalkForwardSpec(
            window_type=WindowType.EXPANDING if window == "expanding" else WindowType.ROLLING,
            min_train_sessions=int(cfg.get("min_train_sessions", 60)),
            test_window_sessions=int(cfg.get("test_window_sessions", 12)),
            step_sessions=int(cfg.get("step_sessions", 12)),
            purge_sessions=int(cfg.get("purge_sessions", 1)),
            embargo_sessions=int(cfg.get("embargo_sessions", 1)),
        )

    def compare_models(
        self,
        dataset_id: str = "DATASET-US-30Y-v001",
        walk_forward_config_path: str | Path = "configs/ml/walk-forward-v1.yaml",
        model_names: str = "composite,ridge,gbdt",
        start_date: date | None = None,
        end_date: date | None = None,
        label_horizon: int = 21,
        output_path: Path | None = None,
    ) -> ModelComparisonResult:
        """Benchmark the ranking models on a real point-in-time panel.

        The panel is one row per instrument per month-end, features are that date's
        factor scores, and the label is the cross-sectional rank of the next month's
        tradable return. Folds are purged and embargoed so a training month whose label
        window overlaps the test block never reaches the model.
        """
        panel = self._panel(dataset_id, start_date, end_date, label_horizon)
        labelled = tuple(row for row in panel.rows if row.label is not None)
        if not labelled:
            raise ValueError(f"Dataset '{dataset_id}' produced no labelled ML rows")

        dataset = MLDataset(
            dataset_id=panel.dataset_id,
            feature_names=panel.feature_names,
            rows=labelled,
        )

        # Folds are cut on the monthly rebalance grid, not on raw trading days: the
        # observation unit is the monthly cross-section, so a purge of one period means
        # one rebalance, which is exactly the label horizon.
        sessions = list(dataset.sessions)
        spec = self._load_walk_forward_spec(walk_forward_config_path)
        folds = PurgedWalkForwardCV.split(sessions, spec)
        if not folds:
            raise ValueError(
                f"Panel of {len(sessions)} monthly cross-sections is too short for a "
                f"walk-forward with {spec.min_train_sessions} training periods"
            )

        requested = tuple(name.strip() for name in model_names.split(",") if name.strip())
        result = ModelComparisonRunner.run_comparison(
            dataset,
            folds,
            model_names=requested or None,
        )

        out_file = output_path or self._base_dir / "artifacts" / "latest" / "model-comparison.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        payload = result.as_dict()
        payload["panel"] = {
            "dataset_id": dataset_id,
            "features": list(dataset.feature_names),
            "label": f"cross-sectional rank of {label_horizon}-session forward return",
            "monthly_cross_sections": len(sessions),
            "labelled_rows": len(labelled),
            "first_session": sessions[0].isoformat(),
            "last_session": sessions[-1].isoformat(),
            "purge_periods": spec.purge_sessions,
            "embargo_periods": spec.embargo_sessions,
        }
        with open(out_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

        return result

    @staticmethod
    def _shuffled_panel(panel: MLDataset, rng: random.Random) -> MLDataset:
        """Permute labels within each cross-section, keeping features untouched."""
        by_session: dict[date, list[MLFeatureRow]] = {}
        for row in panel.rows:
            if row.label is not None:
                by_session.setdefault(row.session, []).append(row)

        shuffled_rows: list[MLFeatureRow] = []
        for session in sorted(by_session):
            rows = by_session[session]
            labels = [float(r.label or 0.0) for r in rows]
            rng.shuffle(labels)
            shuffled_rows.extend(
                MLFeatureRow(
                    session=row.session,
                    instrument_id=row.instrument_id,
                    features=row.features,
                    label=labels[idx],
                )
                for idx, row in enumerate(rows)
            )

        return MLDataset(
            dataset_id=f"{panel.dataset_id}-LABEL-SHUFFLED",
            feature_names=panel.feature_names,
            rows=tuple(shuffled_rows),
        )

    def run_label_shuffle_control(
        self,
        dataset_id: str = "DATASET-US-30Y-v001",
        walk_forward_config_path: str | Path = "configs/ml/walk-forward-v1.yaml",
        seed: int = 20240819,
        permutations: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
        label_horizon: int = 21,
    ) -> LabelShuffleControl:
        """Permutation test: does the measured skill survive breaking the label link?

        Shuffling labels within each cross-section removes any relationship between
        features and outcome while leaving everything else - the folds, the purge, the
        cross-sectional structure, the label distribution - exactly as it was. A model
        that still scores is being rewarded by something other than prediction.

        A single shuffle is not enough to conclude anything. Models are refit per fold,
        so the per-session ICs inside a fold are driven by one fitted model and a
        24-fold study has an effective sample size closer to 24 than to 288; one draw
        landing above the real score is unremarkable. Running several permutations and
        reporting where the real score falls in that distribution is what turns the
        control into a test rather than a coin flip.
        """
        panel = self._panel(dataset_id, start_date, end_date, label_horizon)
        spec = self._load_walk_forward_spec(walk_forward_config_path)

        real_folds = PurgedWalkForwardCV.split(list(panel.sessions), spec)
        real = ModelComparisonRunner.run_comparison(
            MLDataset(
                dataset_id=panel.dataset_id,
                feature_names=panel.feature_names,
                rows=tuple(row for row in panel.rows if row.label is not None),
            ),
            real_folds,
        )

        rng = random.Random(seed)
        permuted: list[ModelComparisonResult] = []
        for _ in range(max(1, permutations)):
            shuffled = self._shuffled_panel(panel, rng)
            folds = PurgedWalkForwardCV.split(list(shuffled.sessions), spec)
            permuted.append(ModelComparisonRunner.run_comparison(shuffled, folds))

        verdicts: list[ShuffleVerdict] = []
        for report in real.reports:
            null_scores = [
                run_report.mean_ic
                for run in permuted
                for run_report in run.reports
                if run_report.model_name == report.model_name
            ]
            if not null_scores:
                continue
            at_least_as_extreme = sum(1 for score in null_scores if score >= report.mean_ic)
            # Add-one smoothing: with n permutations the smallest attainable p-value is
            # 1/(n+1), and reporting an unqualified zero from five draws would overstate
            # the evidence.
            p_value = (at_least_as_extreme + 1) / (len(null_scores) + 1)
            verdicts.append(
                ShuffleVerdict(
                    model_name=report.model_name,
                    observed_rank_ic=report.mean_ic,
                    null_mean=sum(null_scores) / len(null_scores),
                    null_max=max(null_scores),
                    permutations=len(null_scores),
                    p_value=p_value,
                )
            )

        return LabelShuffleControl(real=real, permuted=tuple(permuted), verdicts=tuple(verdicts))
