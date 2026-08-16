# QuantLab Active Red Teaming & Falsification Suite (V1)

## Overview
QuantLab incorporates automated red teaming attacks to prove that its validation defenses catch common quantitative research bugs and fraudulent alpha illusions.

---

## Flagship Demonstration Cases

### Case 1: Future Information Leakage Canary (`lookahead.yaml`)
- **Vulnerability**: Contaminating current factor snapshot with $t+1$ forward price return.
- **Unprotected Outcome**: Wildly attractive equity curve (Sharpe $4.5+$).
- **QuantLab Defense**: `HardGateEvaluator.evaluate_leakage` detects lookahead timestamps, forcing verdict = `REJECTED`.

### Case 2: Multi-Trial Random Mining (`random-mining.yaml`)
- **Vulnerability**: Mining 100 Gaussian white-noise series until a lucky random walk achieves in-sample Sharpe $1.6+$.
- **Unprotected Outcome**: False discovery claimed as genuine alpha.
- **QuantLab Defense**: `DeflatedSharpeCalculator` discounts observed Sharpe for 100 independent trials, emitting multiple-testing warning and forcing verdict = `RESEARCH_ONLY`.

### Case 3: Frictional Illusion & Micro-Edge Fragility (`cost-illusion.yaml`)
- **Vulnerability**: High turnover (25x annual) capturing fractional spread gains that vanish under realistic costs.
- **Unprotected Outcome**: Zero-cost backtest shows positive slope.
- **QuantLab Defense**: `ExecutionStressTester` sweeps friction grid [0, 5, 10, 20, 50] bps; break-even friction is $6.0$ bps (< 10 bps threshold), forcing verdict = `RESEARCH_ONLY`.
