"""Walk-forward model comparison and champion selection runner."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from quantlab.ml.contracts import MLDataset
from quantlab.ml.evaluation import MLEvaluationEngine, ModelEvaluationReport
from quantlab.ml.models.linear import RidgeRanker
from quantlab.ml.models.tree import LightGBMRanker
from quantlab.ml.preprocessing import TrainOnlyPreprocessor
from quantlab.ml.splits import FoldSplit


@dataclass(frozen=True, slots=True)
class ModelComparisonResult:
    champion_model: str
    champion_reason: str
    reports: tuple[ModelEvaluationReport, ...]
    n_folds: int
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "champion_model": self.champion_model,
            "champion_reason": self.champion_reason,
            "reports": [r.as_dict() for r in self.reports],
            "n_folds": self.n_folds,
            "content_hash": self.content_hash,
        }


class ModelComparisonRunner:
    """Runs purged walk-forward comparison across Heuristic Composite, Ridge, and LightGBM."""

    @classmethod
    def run_comparison(
        cls,
        dataset: MLDataset,
        folds: Sequence[FoldSplit],
        composite_weights: Mapping[str, float] | None = None,
    ) -> ModelComparisonResult:
        c_weights = composite_weights or {
            "momentum_12_1": 0.50,
            "value_composite": 0.30,
            "quality_roe": 0.20,
        }

        # Predictions container for each model across test folds
        composite_evals: list[tuple[Sequence[float], Sequence[float]]] = []
        ridge_evals: list[tuple[Sequence[float], Sequence[float]]] = []
        lgbm_evals: list[tuple[Sequence[float], Sequence[float]]] = []

        feat_names = dataset.feature_names

        for fold in folds:
            train_rows = [
                r
                for r in dataset.rows
                if fold.train_start <= r.session <= fold.train_end and r.label is not None
            ]
            test_rows = [
                r
                for r in dataset.rows
                if fold.test_start <= r.session <= fold.test_end and r.label is not None
            ]

            if not train_rows or not test_rows:
                continue

            X_train = [list(r.features) for r in train_rows]
            y_train = [float(r.label or 0.0) for r in train_rows]

            # Fit train-only preprocessor
            preprocessor = TrainOnlyPreprocessor.fit(X_train)
            X_train_trans = preprocessor.transform(X_train)

            # Fit Ridge
            ridge_model = RidgeRanker.fit(X_train_trans, y_train, alpha=1.0)

            # Fit LightGBM
            lgbm_model = LightGBMRanker.fit(
                X_train_trans, y_train, n_estimators=20, learning_rate=0.05, max_depth=3
            )

            # Evaluate per test session
            test_sessions = sorted({r.session for r in test_rows})
            for s in test_sessions:
                s_rows = [r for r in test_rows if r.session == s]
                if len(s_rows) < 3:
                    continue

                X_test_s = [list(r.features) for r in s_rows]
                y_test_s = [float(r.label or 0.0) for r in s_rows]

                # 1. Composite heuristic predictions
                c_preds: list[float] = []
                for r in s_rows:
                    score = sum(
                        float(r.features[i]) * c_weights.get(feat_names[i], 1.0 / len(feat_names))
                        for i in range(len(feat_names))
                    )
                    c_preds.append(score)
                composite_evals.append((c_preds, y_test_s))

                # 2. Ridge predictions
                X_test_trans = preprocessor.transform(X_test_s)
                r_preds = ridge_model.predict(X_test_trans)
                ridge_evals.append((r_preds, y_test_s))

                # 3. LightGBM predictions
                l_preds = lgbm_model.predict(X_test_trans)
                lgbm_evals.append((l_preds, y_test_s))

        # Generate reports
        rep_comp = MLEvaluationEngine.evaluate_model("composite", composite_evals)
        rep_ridge = MLEvaluationEngine.evaluate_model("ridge", ridge_evals)
        rep_lgbm = MLEvaluationEngine.evaluate_model("lightgbm", lgbm_evals)

        reports = (rep_comp, rep_ridge, rep_lgbm)

        # Champion Selection Rule:
        # If ML (Ridge/LGBM) has Rank IC > composite IC + 0.005, promote ML champion
        # Otherwise, Composite remains champion (defending against complexity theater)
        best_report = max(reports, key=lambda r: r.mean_ic)
        if best_report.model_name != "composite" and best_report.mean_ic > rep_comp.mean_ic + 0.005:
            champion = best_report.model_name
            reason = (
                f"Demonstrated incremental out-of-sample Rank IC of "
                f"{best_report.mean_ic:.4f} vs composite {rep_comp.mean_ic:.4f}"
            )
        else:
            champion = "composite"
            reason = "Simple heuristic composite selected as champion due to superior parsimony"

        payload = {
            "champion": champion,
            "reason": reason,
            "reports": [r.as_dict() for r in reports],
            "n_folds": len(folds),
        }
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return ModelComparisonResult(
            champion_model=champion,
            champion_reason=reason,
            reports=reports,
            n_folds=len(folds),
            content_hash=chash,
        )
