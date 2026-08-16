"""Tests for factor ablation and contribution analysis."""

from quantlab.validation.ablation import AblationAnalyzer


def test_factor_ablation_evaluates_marginal_contribution() -> None:
    baseline_sharpe = 1.50
    baseline_cagr = 0.20

    ablation_map = {
        "momentum": (1.10, 0.14),  # omitting momentum hurts Sharpe by 0.40
        "value": (1.40, 0.18),  # omitting value hurts Sharpe by 0.10
    }

    records = AblationAnalyzer.evaluate(baseline_sharpe, baseline_cagr, ablation_map)
    assert len(records) == 2

    mom_rec = next(r for r in records if r.omitted_factor == "momentum")
    assert mom_rec.marginal_contribution_sharpe == 0.40
