"""Walk-forward model comparison and champion selection runner."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from quantlab.ml.contracts import MLDataset
from quantlab.ml.evaluation import MLEvaluationEngine, ModelEvaluationReport
from quantlab.ml.models.linear import RidgeRanker
from quantlab.ml.models.tree import GradientBoostedRanker
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


# How much out-of-sample rank IC a model must add over the composite baseline before it
# is worth the extra moving parts. Roughly the standard error of a rank IC estimated
# from a few hundred monthly cross-sections, so smaller gaps are not distinguishable
# from noise.
MIN_INCREMENTAL_RANK_IC = 0.005


def _zscore(values: Sequence[float]) -> list[float]:
    """Standardize a cross-section so features with different units are comparable."""
    n = len(values)
    if n == 0:
        return []
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance < 1e-18:
        return [0.0] * n
    sd = math.sqrt(variance)
    return [(v - mean) / sd for v in values]


class ModelComparisonRunner:
    """Purged walk-forward comparison of the composite baseline against ranking models."""

    @classmethod
    def run_comparison(
        cls,
        dataset: MLDataset,
        folds: Sequence[FoldSplit],
        composite_weights: Mapping[str, float] | None = None,
        model_names: Sequence[str] | None = None,
    ) -> ModelComparisonResult:
        feat_names = dataset.feature_names
        # An equal-weight composite over standardized features is the honest baseline:
        # it is what a researcher would write before reaching for a model, and every
        # ML result has to beat it by enough to justify the extra machinery (spec 4.2).
        c_weights = composite_weights or dict.fromkeys(feat_names, 1.0 / max(1, len(feat_names)))

        # Predictions container for each model across test folds
        composite_evals: list[tuple[Sequence[float], Sequence[float]]] = []
        ridge_evals: list[tuple[Sequence[float], Sequence[float]]] = []
        gbdt_evals: list[tuple[Sequence[float], Sequence[float]]] = []

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

            gbdt_model = GradientBoostedRanker.fit(
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

                # 1. Composite baseline, standardized within the cross-section so a
                # factor measured in percent cannot outvote one measured in ratio terms.
                standardized = [
                    _zscore([float(r.features[i]) for r in s_rows]) for i in range(len(feat_names))
                ]
                c_preds = [
                    sum(
                        standardized[i][row_idx] * c_weights.get(feat_names[i], 0.0)
                        for i in range(len(feat_names))
                    )
                    for row_idx in range(len(s_rows))
                ]
                composite_evals.append((c_preds, y_test_s))

                # 2. Ridge predictions
                X_test_trans = preprocessor.transform(X_test_s)
                r_preds = ridge_model.predict(X_test_trans)
                ridge_evals.append((r_preds, y_test_s))

                # 3. Gradient boosted tree predictions
                g_preds = gbdt_model.predict(X_test_trans)
                gbdt_evals.append((g_preds, y_test_s))

        # Generate reports
        rep_comp = MLEvaluationEngine.evaluate_model("composite", composite_evals)
        rep_ridge = MLEvaluationEngine.evaluate_model("ridge", ridge_evals)
        rep_gbdt = MLEvaluationEngine.evaluate_model("gbdt", gbdt_evals)

        available = {"composite": rep_comp, "ridge": rep_ridge, "gbdt": rep_gbdt}
        selected = tuple(model_names) if model_names else tuple(available)
        reports = tuple(available[name] for name in selected if name in available) or (
            rep_comp,
            rep_ridge,
            rep_gbdt,
        )

        # The baseline keeps the title unless a model beats it by a margin larger than
        # the noise in the estimate. Ranking by raw score alone would crown whichever
        # model got luckier on the test folds and call it a finding (spec 4.2, 4.14).
        best_report = max(reports, key=lambda r: r.mean_ic)
        margin = MIN_INCREMENTAL_RANK_IC
        beats_baseline = best_report.mean_ic > rep_comp.mean_ic + margin
        if best_report.model_name != "composite" and beats_baseline:
            champion = best_report.model_name
            reason = (
                f"{best_report.model_name} beat the composite baseline out of sample by "
                f"{best_report.mean_ic - rep_comp.mean_ic:+.4f} rank IC "
                f"({best_report.mean_ic:.4f} vs {rep_comp.mean_ic:.4f}), clearing the "
                f"{margin:.3f} margin required to justify the added complexity"
            )
        else:
            champion = "composite"
            reason = (
                f"No model cleared the composite baseline ({rep_comp.mean_ic:.4f} rank IC) "
                f"by the {margin:.3f} margin required, so the simpler model keeps the slot"
            )

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
