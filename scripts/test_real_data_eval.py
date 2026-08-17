"""Test real market data factor research and backtest."""

from datetime import date
from quantlab.application.factor_research import FactorResearchService
from quantlab.application.models import ModelService

svc = FactorResearchService()
res = svc.run_factor_research(
    factor_id="momentum_12_1",
    dataset_id="DATASET-US-MEGACAP-v001",
    start_date=date(2021, 1, 1),
    end_date=date(2024, 12, 31),
)

print("=== REAL DATA FACTOR RESEARCH RESULT ===")
print("Factor ID       :", res.factor_id)
print("Sessions Count  :", res.num_sessions)
print("IC Mean         :", f"{res.ic_mean:+.4f}")
print("IC Std          :", f"{res.ic_std:.4f}")
print("IR (IC / Std)   :", f"{res.ic_ir:+.4f}")
print("Positive IC %   :", f"{res.ic_positive_pct * 100:.1f}%")
print("Rank IC Mean    :", f"{res.rank_ic_mean:+.4f}")
print("Quantiles       :", {k: f"{v*100:+.2f}%" for k, v in res.quantile_returns.items()})
print("Spread (Q5 - Q1):", f"{res.spread_q5_minus_q1 * 100:+.2f}%")
print("Decay Profile   :", {k: f"{v:+.4f}" for k, v in res.decay_profile.items()})

print("\n=== REAL DATA ML MODEL BENCHMARK ===")
ml_svc = ModelService()
ml_res = ml_svc.compare_models(dataset_id="DATASET-US-MEGACAP-v001")
print("Champion Model  :", ml_res.champion_model.upper())
print("Reason          :", ml_res.champion_reason)
for rep in ml_res.reports:
    print(f"Model: {rep.model_name.upper():25} -> OOS Rank IC: {rep.mean_ic:.4f} | IR: {rep.ic_ir:.2f} | Spread: {rep.top_bottom_spread:.4f} | Monotonic: {rep.is_monotonic}")
