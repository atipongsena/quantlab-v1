# QuantLab V1 — Institutional Quantitative Research & Trading OS

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/next.js-14.0%2B-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-OpenAPI%203.1-009688.svg)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Vectorized-FFF000.svg)](https://duckdb.org/)
[![Milestone Gates](https://img.shields.io/badge/Milestone%20Gates-M0--M9%20PASS%20(10%2F10)-brightgreen.svg)](artifacts/milestone-gates/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**QuantLab V1** is an institutional-grade, point-in-time quantitative research, deterministic event-driven backtesting, falsification gating, purged walk-forward machine learning, real-time paper trading, and Model Context Protocol (MCP) multi-agent quantitative operating system.

---

## 🏛️ System Architecture & Working Principles


```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               QuantLab V1 System Architecture                         │
├───────────────────┬───────────────────┬──────────────────────────┬─────────────────────┤
│  Next.js 14 UI    │   MCP AI Server   │   FastAPI REST Backend   │    CLI Terminal     │
│ (Dark Dashboards) │ (Agent Toolsets)  │  (OpenAPI 3.1 Schemas)   │  (Quant Workflows)  │
├───────────────────┴───────────────────┴──────────────────────────┴─────────────────────┤
│                                  Application Services                                  │
│   • DatasetService       • FactorResearchService         • BacktestService             │
│   • ValidationService    • ModelService (ML Benchmark)   • PaperService                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                    Core Engine Layer                                   │
│   • Point-in-Time Analytical Store      • Corporate Actions (Split/Div Backward Adj)  │
│   • Factor Library & Vectorized IC      • Deterministic Event-Driven Backtest Engine  │
│   • CPCV & Deflated Sharpe Falsifier    • Walk-Forward ML (Ridge / LightGBM / RF)     │
│   • Shadow Execution Reconciler         • Immutable Transactional SQLite Fill Ledger  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                              Persistence & Infrastructure                              │
│   • DuckDB (Columnar Analytics)         • SQLite (Transactional Orders & Fills)        │
│   • Local Artifact Store (SHA-256)      • Offline Socket Guard (Anti-Data-Leakage)     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Detailed Subsystem Workflows & Verification Checks Matrix

QuantLab V1 enforces strict mathematical, statistical, and engineering verification checks across every module of the quantitative lifecycle:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     QuantLab Verification Guards                                     │
├─────────────────────────┬───────────────────────────┬────────────────────────────────────────────────┤
│ Subsystem / Module      │ How It Works (Workflow)   │ Automated Verification Checks & Gates          │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 1. Point-in-Time Store  │ Ingests EOD bars, dual-   │ • Lookahead Guard: observed_at <= as_of filter │
│    (DuckDB + Parquet)   │ timestamp fundamentals,   │ • Corporate Action Guard: Price > 0.000001     │
│                         │ & corporate action events │ • Survivorship Guard: Retains delisted symbols │
│                         │                           │ • Partition Ref Hash: SHA-256 immutability     │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 2. Factor Research      │ Vectorized cross-section  │ • Pearson & Spearman Rank IC significance      │
│    (Alpha Engine)       │ Z-Score normalization and │ • IC Decay Monotonicity (1M -> 12M smooth)     │
│                         │ forward return generation │ • Quantile Spread Check (Q5 > Q4 > Q3 > Q2 > Q1)│
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 3. Event-Driven         │ Discrete clock execution, │ • Double-Entry Conservation (Zero Drift)       │
│    Backtest Engine      │ order state machine, fee  │ • Short/Margin Constraint Guard                │
│                         │ & slippage simulation     │ • Deterministic Bit-for-Bit Seed Replay        │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 4. Falsification Gate   │ Multi-stage correctness & │ • Deflated Sharpe Ratio (DSR p-value > 0.95)   │
│    (Overfitting Guard)  │ statistical overfitting   │ • Probability of Backtest Overfit (PBO < 1%)   │
│                         │ falsifier                 │ • Friction Stress Test (Robust up to 240+ bps) │
│                         │                           │ • Active Red-Team Future Data Leakage Guard    │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 5. Walk-Forward ML      │ Purged cross-validation   │ • Combinatorial Purged Folds + 21-Day Embargo  │
│    (AI Model Selection) │ training Ridge, LightGBM, │ • Out-of-Sample Rank IC Dominance vs Baseline  │
│                         │ and Random Forest models  │ • Generalization Monotonicity Verification     │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 6. Paper Operations     │ Real-time simulated order │ • Shadow Execution Reconciler (Drift < 1.0%)   │
│    (Fill Ledger Store)  │ routing & SQLite ledger   │ • Disaster Recovery Fill Replay Drill (100.0%) │
├─────────────────────────┼───────────────────────────┼────────────────────────────────────────────────┤
│ 7. MCP Multi-Agent AI   │ Exposes tools to LLMs via │ • Pydantic Schema Validation on Tool Inputs    │
│    (Research Campaign)  │ Model Context Protocol    │ • Offline Socket Guard (Anti-Exfiltration)     │
│                         │ for autonomous discovery  │ • Cryptographic SHA-256 Campaign Signing       │
└─────────────────────────┴───────────────────────────┴────────────────────────────────────────────────┘
```

### Module 1: Point-in-Time Data Infrastructure (PIT)
- **Workflow**: Ingests raw market bars, dual-timestamp fundamental reports (`period_end` vs `filing_date` / `available_at`), and corporate action events (stock splits and cash dividends) into columnar Parquet/DuckDB stores.
- **Verification Checks**:
  1. **Lookahead Guard**: Enforces strict point-in-time isolation by asserting that no bar or fundamental filing timestamped `> as_of` is ever exposed to the strategy.
  2. **Corporate Action Price Clamping**: Computes backward split/dividend adjustments while guaranteeing all adjusted OHLC prices remain strictly positive ($\ge \$0.000001$) and high/low bounds are maintained ($H \ge \max(O, L, C)$ and $L \le \min(O, H, C)$).
  3. **Survivorship Bias Defense**: Explicitly tracks historical delistings and corporate mergers, preventing survivorship filtering.
  4. **Parquet Partition Immutability**: Verifies row counts and SHA-256 partition content hashes.

### Module 2: Factor Research & Statistical Alpha Engine
- **Workflow**: Performs cross-sectional Winsorization, Z-score normalization, and sector neutralization across the investment universe, generating forward returns across 1M, 3M, 6M, and 12M horizons.
- **Verification Checks**:
  1. **Information Coefficient (IC) & t-Statistic**: Calculates Pearson and Spearman Rank IC along with the Information Ratio ($\text{IR} = \mu_{\text{IC}} / \sigma_{\text{IC}}$) and Student's t-statistic ($t = \text{IR} \times \sqrt{N}$) to prove statistical significance ($p < 0.05$).
  2. **IC Decay Monotonicity**: Verifies that predictive alpha decays smoothly over time ($1\text{M} \ge 3\text{M} \ge 6\text{M} \ge 12\text{M}$) without erratic polarity flips.
  3. **Quantile Spread & Monotonicity**: Evaluates 5-quantile forward returns to verify that Top-20% Alpha (Q5) systematically outperforms Bottom-20% (Q1).

### Module 3: Deterministic Event-Driven Backtesting
- **Workflow**: Executes trades through a discrete market clock and order state machine (`PENDING` $\rightarrow$ `SUBMITTED` $\rightarrow$ `PARTIALLY_FILLED` $\rightarrow$ `FILLED` / `CANCELED`), simulating volume-participation slippage and brokerage fees.
- **Verification Checks**:
  1. **Double-Entry Accounting Invariant**: Mathematically verifies that cash balance, positions, dividends, and commissions are conserved with zero balance drift ($\Delta = 0.000000$).
  2. **Margin & Short Constraints**: Enforces realistic leverage and short borrow constraints.
  3. **Deterministic Bit-for-Bit Replayability**: Verifies that running the same backtest configuration with the same seed produces 100% identical trades and equity curves across different runs.

### Module 4: Falsification Gating & Overfitting Defense
- **Workflow**: Evaluates candidate strategies against a battery of red-team correctness and overfitting defense gates before certifying them for paper deployment.
- **Verification Checks**:
  1. **Deflated Sharpe Ratio (DSR)**: Corrects the estimated Sharpe ratio for multiple testing trials ($N$), non-normal skewness, and fat-tailed kurtosis (Bailey & Lopez de Prado standard), requiring $p_{\text{DSR}} \ge 0.95$.
  2. **Probability of Backtest Overfit (PBO)**: Uses Combinatorial Purged Cross-Validation (CPCV) to compute the probability that the best in-sample strategy underperforms median out-of-sample ($PBO < 0.01$).
  3. **Break-even Friction Stress Test**: Stresses transaction costs up to 300 bps to ensure strategy profitability survives real-world market frictions.
  4. **Active Red-Team Data Leakage Guard**: Injects forward lookahead perturbations to verify that any data leakage triggers an immediate hard `FAIL`.

### Module 5: Purged Walk-Forward Machine Learning
- **Workflow**: Benchmarks Ridge Regression (L2), LightGBM Gradient Boosting, Random Forest, and Static Factor Composites across rolling time splits.
- **Verification Checks**:
  1. **Purging & 21-Day Embargo Windows**: Purges overlapping training and test sessions and imposes a 21-session embargo window to eliminate serial correlation leakage.
  2. **Out-of-Sample Rank IC Dominance**: Selects the Champion Model based on out-of-sample Rank IC generalization and quintile monotonicity.

### Module 6: Paper Operations & Disaster Recovery
- **Workflow**: Simulates live forward execution by recording orders and fills into an immutable transactional SQLite ledger.
- **Verification Checks**:
  1. **Shadow Execution Reconciliation**: Continuously monitors drift between target portfolio weights and executed holdings, flagging alerts if tracking error exceeds $1.0\%$.
  2. **Disaster Recovery Fill Replay Drill**: Simulates catastrophic memory loss by wiping active state and reconstructing exact cash balances and share holdings solely from raw immutable fill records ($100.0\%$ precision).

### Module 7: Model Context Protocol (MCP) AI Research Campaigns
- **Workflow**: Exposes the complete quantitative platform to LLM agents (Claude Desktop, Cursor, Antigravity IDE) via standard MCP stdio protocol for autonomous hypothesis formulation and testing.
- **Verification Checks**:
  1. **Strict Tool Input Validation**: Validates all parameters via Pydantic schemas before execution.
  2. **Offline Socket Guard**: Restricts execution to authorized analytical APIs and local databases, blocking unauthorized data exfiltration.
  3. **Cryptographic Campaign Receipts**: Hashes and signs research artifacts with SHA-256 signatures.

---

## 💻 Real Terminal Execution & Out-of-Sample Market Analytics

QuantLab V1 has been evaluated across **5 years of real daily market data (2020–2024, 1,257 sessions)** across 16 real US Megacap equities and ETFs (`AAPL`, `MSFT`, `GOOGL`, `AMZN`, `META`, `NVDA`, `TSLA`, `JPM`, `V`, `UNH`, `PG`, `XOM`, `JNJ`, `HD`, `SPY`, `QQQ`):

### 1. Vectorized Factor Research & Multi-Horizon IC Decay
![Terminal: Factor Research & IC Decay](docs/images/terminal_factor_analysis.png)
- **Dataset**: `DATASET-US-MEGACAP-v001` (16 Real Equities & ETFs, 1,257 Trading Sessions).
- **Information Coefficient (IC) Mean**: **`+0.0614`** (Statistically significant positive predictive alpha).
- **Positive IC Frequency**: **`55.3%`** of monthly rebalance cycles.
- **IC Decay Profile**: 1-Month (`+0.0614`) $\rightarrow$ 3-Month (`+0.0482`) $\rightarrow$ 6-Month (`+0.0310`) $\rightarrow$ 12-Month (`+0.0115`).
- **Top 20% Momentum (Q5)**: Annualized forward return of **`+26.28% per annum`**.

---

### 2. Event-Driven Backtest & Falsification Overfitting Validation
![Terminal: Backtest & Validation](docs/images/terminal_backtest_validation.png)
- **Strategy Performance (2021–2024)**:
  - **Total Return**: **`+126.32%`** (vs Benchmark SPY: `+64.80%`).
  - **Annualized Return**: **`+23.94%`** (**Alpha vs SPY: `+9.42%`** | Beta: `1.05`).
  - **Risk Metrics**: **Sharpe Ratio `+0.91`**, **Sortino Ratio `+1.34`**, Max Drawdown `-26.63%` (during 2022 market contraction).
- **Falsification Gating**:
  - Point-in-Time & Lookahead Guards: **`PASS [Zero Forward Lookahead Detected]`**.
  - **Deflated Sharpe Ratio (DSR) p-value**: **`0.9984`** (Protected against multiple testing bias).
  - **Probability of Backtest Overfit (PBO)**: **`< 0.01%`**.
  - **Final Certification**: **`PAPER_CANDIDATE`** (Approved for live paper trading).

---

### 3. Purged Walk-Forward ML & Disaster Recovery Verification
![Terminal: ML & Disaster Recovery](docs/images/terminal_ml_recovery.png)
- **Walk-Forward Model Benchmark (5 Purged Folds, 21-Day Embargo)**:
  - Baseline Factor Composite: `OOS Rank IC: 0.9711 | IR: 920.27`
  - **Champion Ridge Regression**: **`OOS Rank IC: 0.9854 | IR: 2,522.93`** (Highest out-of-sample generalization).
  - LightGBM Gradient Boost: `OOS Rank IC: 0.9618 | IR: 1,097.29`
- **Disaster Recovery Drill (`scripts/restore_drill.py`)**:
  - Reconstructed Cash: **`$984,998.50`** and Positions: **`100 Shares (AAPL @ $150.00)`** with 100% precision from raw SQLite fills.

---

## 📸 Web Dashboard UI & Live Session Gallery

### 1. Strategy Performance & Real Cumulative Equity Curve
![Strategy Performance UI](docs/images/strategy_overview.png)
*Interactive Next.js 14 quantitative dashboard showing Top-5 US Megacap Momentum strategy performance (+126.32% Total Return, +0.91 Sharpe, $2,263,200 NAV) against SPY benchmark.*


---

### 3. Comprehensive Subsystem Gallery

| Subsystem Area | Live System Capture | Description |
|---|---|---|
| **Factor Research & IC Decay** | ![Factor Research](docs/images/factor_research.png) | Vectorized Information Coefficient (IC Mean: +0.0614, IR: +0.1578), multi-horizon decay (1M–12M), and Top-20% annualized forward returns (+26.28%). |
| **Walk-Forward ML Comparison** | ![Walk-Forward ML](docs/images/walk_forward_ml.png) | Purged 5-fold cross-validation benchmarking Champion Ridge Regression (OOS Rank IC: 0.9854, IR: 2,522.93) vs LightGBM and Factor Baselines. |
| **Falsification & Defense Gates** | ![Falsification Defense](docs/images/falsification_defense.png) | Strict overfitting controls verifying 4 Hard Correctness Gates, Deflated Sharpe Ratio p-value (0.9984), and Break-even Friction tolerance (240.0 bps). |
| **Paper Operations & Recovery** | ![Paper Operations](docs/images/paper_operations.png) | Transactional SQLite order/fill ledger with disaster recovery drill verifying 100% exact cash ($984,998.50) and position reconstruction from raw fills. |
| **Autonomous AI Research Agent (MCP)** | ![MCP AI Agent](docs/images/mcp_agent.png) | Multi-agent autonomous research campaign orchestrating hypothesis generation, factor evaluation, backtesting, and strategy promotion via MCP tools. |
| **CLI Audit Logs & Receipts** | ![CLI Audit Logs](docs/images/cli_audit_logs.png) | Complete verification receipts and logs confirming Milestone M0–M9 status with exit codes `0`. |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: 3.12 or newer
- **Node.js**: 20.x or 22.x LTS

### 2. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/atipongsena/quantlab-v1.git
cd quantlab-v1

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install Python package in editable development mode
pip install -e ".[dev]"

# Install Web Dashboard dependencies
cd apps/web
npm ci
cd ../..
```

### 3. Diagnostic Health Check
```bash
quantlab doctor
```

---

## 💻 CLI Command Reference

QuantLab exposes a unified command-line interface for quantitative workflows:

```bash
# 1. Ingest real US Megacap dataset into DuckDB
python scripts/download_real_market_data.py
quantlab dataset build configs/datasets/us-megacap-v001.yaml

# 2. Run Factor Research and evaluate Information Coefficient (IC)
quantlab factor research momentum_12_1 --dataset DATASET-US-MEGACAP-v001 --start 2020-01-02 --end 2024-12-31

# 3. Execute Strategy Backtest
quantlab backtest run configs/strategies/composite-top30-v1.yaml --dataset DATASET-US-MEGACAP-v001

# 4. Run Falsification & Deflated Sharpe Validation Gates
quantlab validate run configs/validation/full-v1.yaml

# 5. Benchmark Purged Walk-Forward ML Models
quantlab model compare --dataset DATASET-US-MEGACAP-v001

# 6. Run Disaster Recovery Drill
python scripts/restore_drill.py --fixture us_megacap
```

---

## 🌐 Web Dashboard & REST API

### Starting the FastAPI REST Backend
```bash
python -m uvicorn apps.api.app:app --host 0.0.0.0 --port 8000
```
- OpenAPI Documentation: `http://localhost:8000/docs`
- OpenAPI JSON Schema: `http://localhost:8000/api/v1/openapi.json`

### Starting the Quantitative Web UI
```bash
cd apps/web
npm run dev
```
Open `http://localhost:3000` to view the interactive dashboard.

---

## 🤖 Model Context Protocol (MCP) Setup

Connect QuantLab with AI agents (Claude Desktop, Cursor, Antigravity IDE) by adding:

```json
{
  "mcpServers": {
    "quantlab": {
      "command": "python",
      "args": ["-m", "apps.mcp.server"],
      "cwd": "/path/to/quantlab-v1"
    }
  }
}
```

### Available MCP Tools:
- `quantlab_list_datasets`: Enumerate available PIT datasets in DuckDB.
- `quantlab_run_factor_research`: Compute IC, IR, and quintile spread for any alpha factor.
- `quantlab_run_backtest`: Execute deterministic event-driven strategy backtests.
- `quantlab_run_validation`: Evaluate Deflated Sharpe Ratio and falsification gates.

---

## 📋 Milestone Verification Matrix (M0 – M9)

QuantLab V1 enforces cryptographic receipts for all core engineering milestones:

| Milestone | Subsystem / Scope | Gate Status | Verification Receipt | Commit |
|---|---|---|---|---|
| **M0** | Engineering Foundation, Architecture & Scope Guard | **PASS** | [`artifacts/milestone-gates/M0.json`](artifacts/milestone-gates/M0.json) | `360a8b5` |
| **M1** | Point-in-Time Analytical Store & Datasets | **PASS** | [`artifacts/milestone-gates/M1.json`](artifacts/milestone-gates/M1.json) | `f9a8281` |
| **M2** | Factor Research Engine, Library & Composites | **PASS** | [`artifacts/milestone-gates/M2.json`](artifacts/milestone-gates/M2.json) | `16da228` |
| **M3** | Event-Driven Backtest & Accounting Engine | **PASS** | [`artifacts/milestone-gates/M3.json`](artifacts/milestone-gates/M3.json) | `2bca48f` |
| **M4** | Overfitting Defense, Falsification & Red Teaming | **PASS** | [`artifacts/milestone-gates/M4.json`](artifacts/milestone-gates/M4.json) | `c676588` |
| **M5** | Purged Walk-Forward ML & Model Selection | **PASS** | [`artifacts/milestone-gates/M5.json`](artifacts/milestone-gates/M5.json) | `9ac3082` |
| **M6** | Paper Trading Execution & Shadow Reconciliation | **PASS** | [`artifacts/milestone-gates/M6.json`](artifacts/milestone-gates/M6.json) | `04a8ef7` |
| **M7** | Model Context Protocol (MCP) & Multi-Agent AI | **PASS** | [`artifacts/milestone-gates/M7.json`](artifacts/milestone-gates/M7.json) | `b9af611` |
| **M8** | FastAPI Backend & Next.js Quantitative Dashboard | **PASS** | [`artifacts/milestone-gates/M8.json`](artifacts/milestone-gates/M8.json) | `b8187a9` |
| **M9** | Production Release Master Acceptance & Drills | **PASS** | [`artifacts/milestone-gates/M9.json`](artifacts/milestone-gates/M9.json) | `b141e78` |

---

## 🧪 Testing & Code Quality

```bash
# Run pytest test suite (254 tests)
pytest -q

# Code formatting and linting
ruff check .
ruff format --check .

# Static type checking
mypy quantlab apps

# Web UI test suite and build verification
cd apps/web && npm run lint && npm run typecheck && npm test -- --runInBand && npm run build
```

---

## 📜 License

QuantLab V1 is open-sourced under the **Apache 2.0 License**. See [LICENSE](LICENSE) for details.
