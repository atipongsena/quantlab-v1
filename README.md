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

![QuantLab V1 Working Principles Lifecycle](docs/images/quantlab_working_principles.png)

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

## 💻 Live Terminal Execution & Quantitative Analysis

### 1. Vectorized Factor Research & IC Decay Analysis
![Terminal: Factor Research & IC Decay](docs/images/terminal_factor_analysis.png)
*Execution of `quantlab factor research` computing Information Coefficient (IC Mean: +0.0524, IR: +1.86), multi-horizon IC decay, and monotonic quintile forward return spread (+12.20%).*

---

### 2. Event-Driven Backtest & Falsification Overfitting Validation
![Terminal: Backtest & Validation](docs/images/terminal_backtest_validation.png)
*Deterministic execution of `quantlab backtest` (Sharpe: +1.85, Max DD: -4.2%) coupled with `quantlab validate` (Deflated Sharpe p-value: 1.0000, Lookahead Guard: CLEAN).*

---

### 3. Purged Walk-Forward ML & Disaster Recovery Drill
![Terminal: ML & Disaster Recovery](docs/images/terminal_ml_recovery.png)
*Walk-forward cross-validation selecting Champion Ridge Regression (Out-of-Sample Rank IC: 0.9854) and disaster recovery drill verifying 100% exact cash and position reconstruction.*

---

## 📸 Web Dashboard UI & Live Session Gallery

### Interactive Strategy Performance Dashboard
![QuantLab V1 Strategy Overview](docs/images/strategy_overview.png)
*Real-time interactive dashboard displaying strategy equity curves, Sharpe Ratio metrics, factor loadings, and paper operations.*

---

### Live Browser Session Recording
![Live Browser Session Recording](docs/images/quantlab_live_dashboard.webp)

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: 3.12 or newer
- **Node.js**: 20.x or 22.x LTS

### 2. Environment Setup

```bash
# Clone repository
git clone https://github.com/atipongsena/quantlab-v1.git
cd quantlab-v1

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
cd apps/web && npm ci && cd ../..
```

### 3. Verify Installation
```bash
quantlab doctor
```

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

## 📜 License

QuantLab V1 is open-sourced under the **Apache 2.0 License**. See [LICENSE](LICENSE) for details.
