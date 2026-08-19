# QuantLab V1 — Master Design Specification

**Date:** 2026-08-16  
**Status:** Design approved 2026-08-16. Implemented; see the implementation note at the end of this document for where the build deliberately departs from this proposal.  
**Product:** QuantLab  
**Positioning:** Reproducible, point-in-time-aware agentic quantitative research and paper-trading platform  

---

## 0. Executive Summary

QuantLab V1 is a quantitative research platform for **US equities and ETFs** that combines deterministic research infrastructure with a constrained AI research layer. Its purpose is not to maximize backtest CAGR. Its purpose is to make systematic research **reproducible, point-in-time correct, falsifiable, auditable, and forward-testable**.

The system must support this lifecycle:

```text
Question / Hypothesis
        ↓
Point-in-Time Data
        ↓
Historical Universe
        ↓
Factor Research
        ↓
Simple Baseline + ML Challenger
        ↓
Portfolio Construction + Risk
        ↓
Authoritative Event-Driven Backtest
        ↓
Robustness / Falsification / Lockbox
        ↓
Paper Trading + Forward Evidence
        ↓
Agentic Research Report
```

Three principles govern the entire architecture:

1. **Agent proposes. Quant engine proves.**
2. **Every number must be reproducible and traceable.**
3. **A strategy earns promotion by surviving falsification, not by having the prettiest backtest.**

### Locked V1 scope

- Market: US equities + ETFs.
- Frequency: Daily/EOD data; monthly equity rebalance by default.
- Data budget: free-first.
- Equity research universe: historical liquid US equities, target size 1,000 securities where data quality permits.
- Portfolio: long-only, cash account, no leverage, no shorting.
- Baseline portfolio: Top-30, equal weight, monthly rebalance, entry/hold buffer.
- Benchmark: SPY total return methodology.
- Research core: Momentum, Value, Quality, Growth, Low Volatility/Risk.
- ML: simple composite baseline, Ridge baseline, LightGBM learning-to-rank challenger.
- Execution: signals generated after EOD; default fill at next eligible session open plus explicit costs/slippage.
- Deployment: research, authoritative backtest, internal/external paper-trading adapter. No live money in V1.
- Agent role: hypothesis generation, experiment orchestration, critique, and grounded reporting through typed tools.

### Explicit non-goals for V1

No live-money trading, intraday/tick/HFT, options, futures, FX, crypto, shorting, leverage, borrow models, RL, LSTMs/Transformers for price prediction, alternative data, institutional paid-data dependence, 100+ factor libraries, arbitrary LLM-executable strategy code, agent swarms, Kubernetes, Spark, enterprise multi-tenancy, or full tax accounting.

---

# 1. System Architecture

## 1.1 Architectural choice

Use a **custom modular quant platform** rather than making Qlib, LEAN, NautilusTrader, Backtrader, or another framework the application core. Borrow proven patterns from those ecosystems while owning QuantLab's semantics, domain boundaries, experiment lifecycle, and validation logic.

Do not reimplement commodity numerical methods unnecessarily. Libraries may be used for dataframe operations, statistics, optimization, ML, and visualization. QuantLab remains the authority for:

- temporal semantics,
- point-in-time access,
- experiment lineage,
- portfolio/risk rules,
- execution assumptions,
- accounting,
- validation gates,
- forward evidence,
- agent permissions.

## 1.2 Layered architecture

```text
User Interfaces
  Web / CLI / Notebook / MCP
        ↓
Agent / Research Layer
  Research Agent / Experiment Orchestrator / Quant Critic
        ↓ typed tools
Application / Research Services
  Campaigns / Experiments / Registry / Artifacts
        ↓
Deterministic Quant Core
  Data → Universe → Factors → ML → Portfolio → Backtest → Analytics → Validation
        ↓
Paper Trading
  Scheduler → Inference → Orders → Fills → Reconciliation → Forward Evidence
        ↓
Infrastructure
  PostgreSQL / Parquet / DuckDB / Artifact Store / Workers / Scheduler
```

## 1.3 Dependency direction

```text
apps / adapters
      ↓
application services / agents
      ↓
quant modules
      ↓
domain
```

The `domain` package must not import FastAPI, MCP, LLM SDKs, UI code, database-specific implementations, or provider SDKs.

## 1.4 Monorepo structure

```text
quantlab/
├── apps/
│   ├── api/
│   ├── cli/
│   ├── web/
│   ├── worker/
│   └── mcp/
├── quantlab/
│   ├── domain/
│   ├── data/
│   ├── universe/
│   ├── factors/
│   ├── ml/
│   ├── portfolio/
│   ├── backtest/
│   ├── analytics/
│   ├── validation/
│   ├── paper/
│   ├── research/
│   ├── agents/
│   ├── infrastructure/
│   └── common/
├── configs/
├── notebooks/
├── tests/
├── data/
├── artifacts/
├── docs/
│   ├── architecture/
│   ├── research/
│   ├── decisions/
│   └── superpowers/specs/
├── pyproject.toml
└── docker-compose.yml
```

## 1.5 Core domain objects

Do not use raw `DataFrame` objects as every subsystem's public contract. Core domain objects include at minimum:

- `Instrument`
- `SymbolHistory`
- `MarketBar`
- `CorporateAction`
- `Signal` / `AlphaSnapshot`
- `TargetPosition` / `TargetPortfolio`
- `Order`
- `Fill`
- `Position`
- `PortfolioSnapshot`
- `Experiment`
- `DatasetManifest`
- `BacktestResult`
- `ValidationResult`
- `PaperDeployment`

DataFrames/Polars frames are acceptable internal computational representations.

## 1.6 Architecture Decision Records

Maintain ADRs for consequential decisions, including at least:

- custom modular quant core,
- PostgreSQL + Parquet + DuckDB storage split,
- event-driven authoritative backtest,
- agent/deterministic boundary,
- point-in-time temporal semantics,
- modular monolith,
- offline authoritative backtests,
- immutable/versioned artifacts,
- paper recovery/idempotency model,
- security/permission boundaries.

---

# 2. Data Architecture and Point-in-Time Semantics

## 2.1 Core temporal rule

Every data item must distinguish what it describes from when it became usable.

```text
effective_at  = economic/market period represented by the value
available_at  = earliest time the strategy is allowed to know/use the value
```

A datum is eligible only when:

```text
available_at <= decision_time
```

For SEC fundamentals, fiscal period end is not availability time. A fiscal period ending on December 31 but filed on February 20 is unavailable before the filing becomes available.

## 2.2 Internal security identity

Ticker symbols are not primary keys. Use an internal `instrument_id` (UUID or equivalent) plus issuer/security metadata. Maintain versioned symbol history:

```text
instrument_symbol_history
- instrument_id
- symbol
- exchange
- valid_from
- valid_to
- source
```

Ticker changes must not create fake sells/buys.

## 2.3 Provider abstraction

Define interfaces such as:

- `MarketDataProvider`
- `ListingProvider`
- `FundamentalProvider`
- `MacroProvider`
- `CorporateActionProvider`

V1 implementations may use free/public sources such as Yahoo/yfinance-style daily history, SEC EDGAR/XBRL, FRED/ALFRED-style macro data, Nasdaq/public listing information, and Alpha Vantage-style historical listing data where free access and rate limits permit.

The design must tolerate a free source being rate-limited, changed, or unavailable. Provider adapters are replaceable. No provider SDK may leak into Quant Core.

## 2.4 Free-first limitations

QuantLab must not claim institutional-grade survivorship-free data when using free sources. It must explicitly measure and report limitations such as:

- missing delisted price history,
- incomplete corporate-action history,
- imperfect historical listing coverage,
- fundamental normalization edge cases,
- provider revisions,
- licensing/availability constraints.

Data uncertainty is a first-class result, not an inconvenient footnote.

## 2.5 Default research period

Target:

- raw warm-up start: `2010-01-01` where provider coverage permits,
- first eligible backtest date: after sufficient lookback, default `2011-01-01`,
- end: latest fully ingested and published historical session.

Do not silently backtest earlier than the historical listing/universe methodology can support.

## 2.6 Historical equity universe

Do not use today's S&P 500 membership as the historical research universe. Build a monthly point-in-time liquidity universe.

Default target universe: `US_LIQUID_1000`.

At each month-end:

```text
Historical active listings as of date
        ↓
Eligible common equities
        ↓
Valid price history
        ↓
Price >= configurable threshold (baseline $5)
        ↓
Minimum history (baseline 252 sessions)
        ↓
Trailing 60-session median dollar volume
        ↓
Rank by liquidity
        ↓
Top 1,000 where data quality permits
```

All trailing calculations may use only data available on or before the snapshot date.

If delisted/listing coverage is incomplete, set explicit survivorship-risk flags rather than pretending the dataset is perfect.

## 2.7 Equity and ETF universes are separate

Cross-sectional equity factor/ML research uses the historical liquid-equity universe.

ETF tactical allocation uses a curated, versioned, config-driven ETF universe. Do not mix ETFs into equity factor rankings by default.

## 2.8 Raw, normalized, dataset layers

```text
data/
├── raw/          # immutable source snapshots
├── normalized/   # canonical instruments/prices/fundamentals/actions/macro
├── datasets/     # versioned research-ready datasets
└── features/     # materialized features/factors where appropriate
```

Raw snapshots are immutable. New provider/revision downloads create new snapshots.

## 2.9 Daily market-bar schema

Canonical daily bar includes at least:

- `instrument_id`
- `session_date`
- raw OHLC
- raw volume
- provider adjusted close if supplied
- currency
- source provider
- source record/snapshot id
- ingestion timestamp

## 2.10 Price semantics

Maintain explicit concepts for:

- `RAW` — tradable/raw price for execution/accounting,
- `SPLIT_ADJUSTED`,
- `TOTAL_RETURN_ADJUSTED` — for return/factor research where appropriate.

Do not double-count dividends by both using total-return-adjusted prices and crediting the same dividend cash in the same accounting path.

## 2.11 Corporate actions

Support at least:

- dividends,
- splits,
- symbol changes,
- delisting/terminal-value events where data exists.

The event-driven backtester uses raw tradable prices and explicit actions. Missing delisting terminal values must create a severe data-quality flag; do not silently assume last close is realizable.

## 2.12 SEC raw fact store

Store source facts before normalization, including:

- CIK / issuer id,
- taxonomy,
- concept,
- unit,
- period start/end,
- value,
- filing timestamp/date,
- form,
- fiscal year/period,
- accession number,
- raw snapshot id.

Accession/source provenance must remain traceable.

## 2.13 Fundamental normalization

Create versioned mappings to normalized metrics such as:

- revenue,
- net income,
- operating income,
- cash from operations,
- capex,
- book equity,
- total assets,
- shares outstanding.

Each normalized observation retains:

- source concept,
- source filing/accession,
- `period_end`,
- `available_at`,
- normalization version.

## 2.14 Restatement correctness

An amended/revised future filing must not rewrite what a historical strategy supposedly knew. Point-in-time queries choose the latest eligible filing available at the requested time.

## 2.15 Conservative fundamental lag

V1 should support an additional configurable availability/execution lag, baseline one trading session, to avoid assuming instantaneous parsing/trading at filing publication.

## 2.16 Point-in-time market cap

Market cap must combine point-in-time price with shares outstanding known at the time. Do not multiply historical price by current shares outstanding.

## 2.17 Macro vintages

When macro data is used, prefer vintage-aware semantics so revised macro history is not retroactively visible. Macro observations retain observation date and real-time/vintage validity where the source permits it.

## 2.18 Dataset manifest and versioning

Every research dataset has a manifest including:

- dataset id,
- creation time,
- research range,
- provider/snapshot identifiers,
- normalization/universe versions,
- row/instrument counts,
- content/manifest hash,
- data-quality summary.

Experiments reference dataset ids, not “latest data.”

## 2.19 Data confidence and bias flags

Each dataset/experiment reports confidence and explicit flags, e.g.:

- `SURVIVORSHIP_RISK`
- `LOOKAHEAD_RISK`
- `RESTATEMENT_RISK`
- `MISSING_DELISTED_PRICE`
- `CORPORATE_ACTION_UNVERIFIED`
- `FUNDAMENTAL_COVERAGE_LOW`
- `MACRO_REVISION_RISK`

Suggested confidence labels: A/B/C/D, with underlying metrics always available.

## 2.20 Point-in-time query API

Quant modules consume data through time-aware APIs such as:

```text
get_price(instrument, as_of)
get_fundamental(instrument, metric, as_of)
get_universe(universe, as_of)
get_macro(series, as_of)
```

Strategy code must not be encouraged to query raw tables directly.

## 2.21 Data quality gates

Ingestion produces structured quality reports including coverage, duplicates, invalid OHLC, unresolved mappings, corporate-action warnings, stale data, etc.

Severe coverage failures may fail an experiment. Partial data must never be silently treated as complete.

---

# 3. Factor Research Engine

## 3.1 Factor lifecycle

```text
PIT Dataset
  ↓
Raw Features
  ↓
Factor Definition
  ↓
Missing/Staleness Policy
  ↓
Winsorization
  ↓
Normalization / Ranking
  ↓
Optional Neutralization
  ↓
Factor Snapshot
  ↓
Factor Evaluation
  ↓
Factor Registry
```

Creation and evaluation are separate subsystems.

## 3.2 Factor registry

Every factor is versioned and stores:

- id/name/version,
- category,
- description,
- higher/lower-is-better direction,
- required fields,
- lookback,
- availability rules,
- missing-data policy,
- transform config,
- implementation/code hash,
- status: experimental/researched/validated/deprecated.

Changing methodology creates a new factor version.

## 3.3 V1 factor set

Momentum:

- 12-1 momentum,
- 6-1 momentum.

Value:

- earnings yield,
- book-to-market,
- free-cash-flow yield.

Quality:

- ROE,
- ROA,
- gross profitability,
- accrual quality.

Growth:

- revenue growth,
- operating income growth.

Risk:

- 60-day realized volatility,
- 252-day maximum drawdown,
- beta.

Keep V1 to roughly this set; do not build a 100-factor library before the research loop works.

## 3.4 Return inputs

Momentum/return research uses correctly adjusted total-return series or an equivalent corporate-action-aware methodology. Execution remains on raw tradable prices.

## 3.5 Missingness and staleness

Never use a universal `fillna(0)` policy. Factors have explicit statuses such as:

- valid,
- insufficient history,
- missing fundamental,
- invalid denominator,
- stale data,
- out of range.

Stale filings may be rejected according to config.

## 3.6 Cross-sectional transforms

Support:

- percentile winsorization (baseline 1%/99%) or robust alternatives,
- percentile ranking,
- z-score,
- robust z-score,
- direction normalization so higher final score always means more attractive.

## 3.7 Neutralization

Support optional within-sector ranking and regression-style neutralization. Do not force neutralization on every baseline factor.

Sector metadata itself is versioned; unknown sector remains `UNKNOWN` rather than guessed.

## 3.8 Factor availability contract

A composite factor's `available_at` is the maximum availability time of all required inputs. Labels/future returns are a separate namespace and may never be imported by factor runtime.

## 3.9 Factor evaluation

At minimum produce:

- coverage,
- distribution,
- Pearson IC,
- Spearman Rank IC,
- IC time series / IC IR / positive-IC frequency,
- forward-horizon decay (1M/3M/6M/12M as appropriate),
- quantile portfolio returns,
- diagnostic Q5-Q1 spread,
- turnover/rank turnover,
- factor correlation/redundancy,
- subperiod stability,
- sector and size diagnostics.

A long-short diagnostic does not imply V1 supports deployable shorting.

## 3.10 Baseline composite

Use a deterministic configurable baseline, initially:

- Momentum 30%
- Quality 25%
- Value 20%
- Growth 15%
- Low Volatility 10%

This is a baseline, not a claim of optimality. Also retain equal-factor and momentum-only baselines.

## 3.11 Safe factor specification

Agents may compose reviewed factors declaratively. Standard runtime must not expose arbitrary Python `eval`/shell code generation.

A minimal factor DSL may support safe operations such as add/subtract/multiply/divide, rolling mean/std, return, rank, z-score, log, and backward lag. It must not provide a forward `LEAD` operator.

## 3.12 Factor tests

Required tests include formula correctness, no-future-data behavior, split/dividend consistency, missing history, direction, winsorization, ranking ties, and golden synthetic factor rankings.

---

# 4. ML Ranking and Walk-Forward Architecture

## 4.1 ML objective

ML ranks equities cross-sectionally. It does not primarily predict exact future prices.

```text
PIT Features
  ↓
Cross-sectional Panel
  ↓
Temporal Split
  ↓
Purged Walk-Forward Training
  ↓
Ranking Model
  ↓
Out-of-Sample Scores
  ↓
Portfolio
```

## 4.2 Baselines first

Compare all ML against:

- simple multi-factor composite,
- equal-factor baseline,
- Ridge/linear model.

If a complex model does not improve out-of-sample evidence enough to justify its complexity/turnover, keep the simpler baseline.

## 4.3 Monthly panel

Default training/inference observation unit is a monthly cross-section aligned with the monthly rebalance process.

## 4.4 Label semantics

Labels must match the executable timeline. A signal produced after month-end close cannot assume entry at that same close. Default forward label aligns to next-session-open entry and next-rebalance exit/measurement semantics, including corporate actions.

Maintain representations such as raw forward return, benchmark/universe-relative excess return, and cross-sectional rank. The ranking target is the primary V1 ML target.

## 4.5 Label isolation

`labels.*` is a distinct namespace. Feature/factor runtime cannot import labels. Authoritative inference never has label access.

## 4.6 V1 models

- Model 0: deterministic composite.
- Model 1: Ridge/linear baseline.
- Model 2: LightGBM ranker as flagship nonlinear challenger.

Do not add deep learning or RL in V1.

## 4.7 Temporal validation

Random shuffled train/test splits are prohibited for authoritative evaluation.

Support rolling or expanding walk-forward folds. Baseline design: roughly five years training plus validation/test blocks, with configurable retraining schedule (quarterly suggested) and monthly inference.

## 4.8 Purging and embargo

Purge observations whose label horizons overlap validation/test boundaries. Support a configurable embargo, baseline one rebalance period where appropriate.

## 4.9 Cross-sectional grouping

Learning-to-rank grouping is by rebalance date. Securities from different dates are not in the same ranking group.

## 4.10 Hyperparameter discipline

Search space and trial counts are budgeted. Do not tune directly by repeatedly maximizing final backtest Sharpe. Prefer prediction/ranking objectives on validation data, then evaluate final portfolio behavior separately.

Every trial remains in the trial ledger.

## 4.11 Training-only fitted transforms

Any fitted scaler/imputer/encoder learns parameters from training data only. Stateless cross-sectional transforms may use the contemporaneous cross-section when point-in-time valid.

## 4.12 Prediction snapshots

Each prediction snapshot stores model/version, dataset, as-of time, instrument, score/rank/percentile, feature-snapshot reference, and classification:

- TRAIN
- VALIDATION
- TEST
- PAPER_SHADOW
- PAPER_ACTIVE

Authoritative portfolio backtests must reject TRAIN predictions.

## 4.13 Model registry

Store model type/version, training dataset, training range, features, hyperparameters, validation metrics, Git SHA/code fingerprint, artifact URI/hash, and lifecycle state.

## 4.14 Champion/challenger philosophy

The historical winner does not automatically become paper champion. A simple composite may remain champion while LightGBM runs as a shadow challenger.

## 4.15 ML diagnostics

Produce Rank IC, IC stability, quantile returns, feature importance/permutation importance, optional SHAP, importance stability across folds, sector/size/regime diagnostics, turnover, and model drift inputs.

Feature importance is not proof of causality or robustness.

## 4.16 ML tests

Required: temporal split, purge/embargo, label isolation, train-only preprocessing, out-of-sample tag enforcement, ranking groups, reproducibility, deliberate future-feature rejection, label-shuffle collapse test, and synthetic learnable-signal test.

---

# 5. Portfolio Construction and Risk Engine

## 5.1 Separation of responsibility

```text
Model ranks.
Portfolio engine allocates.
Risk engine constrains.
Execution engine trades.
```

A high model score never directly determines an unconstrained position size.

## 5.2 Baseline portfolio

- `US_LIQUID_1000`
- Top 30
- monthly rebalance
- equal weight
- SPY benchmark
- target gross exposure around 99% with configurable cash buffer
- long-only, no leverage

Equal weight is the official baseline because it isolates stock-selection alpha from sizing complexity.

## 5.3 Additional V1 weighting

Support inverse-volatility weighting as a research variant. Score/risk weighting may exist as experimental. Mean-variance optimization is not the default.

## 5.4 Rebalance buffer

Default concept:

- new entry requires Top 30,
- an existing holding may remain while within Top 40.

The exact values are config-driven. This reduces turnover/churn.

## 5.5 Constraints

Support at minimum:

- max single-name weight (baseline 5%),
- max sector weight (baseline 30% as a simple V1 cap),
- unknown-sector cap,
- gross exposure/cash constraints,
- liquidity/ADV participation limits,
- minimum trade value/weight,
- no-trade/rebalance band,
- optional turnover budget.

Hard and soft constraints are distinct. Rules return structured PASS/ADJUST/REJECT outcomes.

## 5.6 Liquidity and capacity

Measure order/position size relative to ADV and provide capacity/day-to-liquidate diagnostics. V1 paper capital may be $1M virtual NAV, but architecture must remain scale-aware.

## 5.7 Fractional shares

Baseline authoritative backtest uses no fractional shares. Order sizing is deterministic and leaves residual cash.

## 5.8 Turnover

Use a documented turnover definition and estimate costs before order generation. Selection/exit priority must be deterministic.

## 5.9 Portfolio snapshots

Persist current/target weights, model rank/score, selection reason, and constraint adjustments. Example reasons:

- TOP_K_ENTRY
- BUFFER_HOLD
- FORCED_EXIT
- SECTOR_CAP_REDUCTION
- LIQUIDITY_CAP
- TURNOVER_LIMIT

## 5.10 Risk engine

Deterministic rules, not AI. Include position, sector, exposure, cash, liquidity, turnover, and data-quality rules.

## 5.11 Diagnostics

Calculate concentration, effective number of positions, Top-5/Top-10 concentration, beta, volatility estimate, tracking error, sector exposure, factor exposure, turnover, and capacity diagnostics.

## 5.12 Tests

Property-based tests verify long-only weights, weight sums, caps, sector constraints, cash, deterministic selection, buffer behavior, conflict handling, symbol-change invariance, split invariance, and no infinite constraint loops.

---

# 6. Authoritative Event-Driven Backtesting and Execution

## 6.1 Authoritative semantics

Fast vectorized research is exploratory. Official performance comes from the authoritative event-driven simulation.

If fast research and authoritative simulation disagree, the authoritative result wins.

## 6.2 Clock

Use a `SimulationClock` abstraction. Backtest uses `HistoricalClock`; paper uses `RealClock`. Core modules must not call wall-clock time directly for market semantics.

Market-session behavior is calendar-driven and timezone-aware (`America/New_York` semantics, UTC internally).

## 6.3 Event types

Support at least session start/end, market data, corporate action, signal/rebalance, order submitted/accepted/cancelled, and fill events.

Document and version event ordering.

## 6.4 Default timeline

```text
Session close
  ↓
EOD data finalized/validated
  ↓
Factors / model inference
  ↓
Target portfolio / risk / orders
  ↓
Orders eligible next session
  ↓
Next session open
  ↓
Fill + slippage/costs
```

Same-close execution is prohibited under the default model.

## 6.5 Order lifecycle

First-class statuses:

- CREATED
- SUBMITTED
- ACCEPTED
- PARTIALLY_FILLED
- FILLED
- REJECTED
- CANCELLED
- EXPIRED

V1 needs market orders only, while leaving domain room for future order types.

## 6.6 Execution model

Default reference price is next eligible session open.

- buy fill = reference open plus adverse slippage,
- sell fill = reference open minus adverse slippage.

No missing-open backfill from previous close without an explicit policy and warning.

## 6.7 Costs

Keep commission, slippage, and market-impact concepts separate. Baseline may use zero commission plus fixed-bps slippage. Run cost-sensitivity scenarios, e.g. 0/5/10/20/50 bps.

Free-first V1 does not pretend to possess historical bid/ask truth. Modeled spread/impact must be labeled as modeled.

## 6.8 Partial fill / participation

Architecture supports maximum participation and partial fills, even if the default $1M portfolio rarely triggers them.

## 6.9 Corporate-action accounting

- split changes share count while preserving economic value,
- dividend credits according to a documented ex/pay-date policy,
- symbol change preserves instrument identity,
- delisting uses observed terminal value when available and explicit uncertainty when not.

## 6.10 Ledger/accounting

Maintain cash, position, transaction, and corporate-action ledgers. Portfolio equity each session is cash plus marked market value. Track realized PnL, unrealized PnL, dividends, and trading costs separately.

V1 uses weighted-average cost and pre-tax performance.

## 6.11 Backtest result

Structured result contains dataset/experiment ids, period, equity curve, returns, orders, fills, positions, costs, metrics, warnings, data-quality status, and engine/version metadata.

## 6.12 Performance metrics

At minimum:

- total return,
- CAGR,
- annualized volatility,
- Sharpe,
- Sortino,
- max drawdown + duration/recovery,
- Calmar,
- beta/alpha methodology,
- tracking error,
- turnover,
- trading costs,
- excess return vs SPY,
- contribution by instrument/sector/period where practical.

Metric definitions and risk-free assumptions are explicit/versioned.

## 6.13 Offline authority

Once a historical dataset is published, authoritative backtests must not call the internet. Missing data is a dataset error/warning, not a trigger to fetch live data mid-run.

## 6.14 Validity status

Backtest result status:

- VALID
- VALID_WITH_WARNINGS
- INVALID

Agents/reports may not hide validity warnings.

## 6.15 Backtest tests

Critical tests: next-open no-lookahead, gap handling, missing open, split, dividend, symbol change, cash conservation, cost accounting, deterministic replay, event ordering, frozen real-market regression, and golden synthetic backtest.

---

# 7. Validation, Robustness, and Backtest-Overfitting Engine

## 7.1 Philosophy

A strategy is not validated because it performed well; it is validated because it survived attempts to falsify it.

## 7.2 Validation ladder

```text
L1 Correctness
L2 Predictive Evidence
L3 Portfolio Robustness
L4 Statistical Robustness
L5 Forward Evidence
```

Correctness failures block everything else.

## 7.3 Research / validation / lockbox separation

Maintain distinct research-development, validation, and locked-holdout partitions. Exact date boundaries are configuration and dataset dependent.

A locked holdout is revealed only after preliminary gates and a frozen strategy specification. Once accessed, it is consumed and cannot be treated as unseen for revised candidates.

## 7.4 Holdout access ledger

Track which human/agent/system accessed which partition, when, and for what purpose. Researcher exposure to a test set matters even when model training did not use it.

## 7.5 Required V1 robustness tests

- parameter neighborhood/stability,
- Top-K sensitivity (20/30/50 baseline set),
- weighting sensitivity (equal vs inverse-vol),
- universe sensitivity where data supports it,
- subperiod/rolling performance,
- sector and leave-one-sector-out diagnostics,
- cost stress,
- next-open vs delayed/alternative execution stress,
- filing availability lag stress,
- strategy/factor ablation,
- ML feature-group ablation,
- block/stationary bootstrap uncertainty,
- trial/multiple-testing ledger,
- negative controls / label shuffle.

## 7.6 Performance plateaus, not spikes

A robust parameterization should have reasonable neighboring performance. Sharp isolated optimum behavior triggers parameter-instability warnings.

## 7.7 Return concentration diagnostics

Measure dependence on best year(s), dominant stock(s), sector(s), or regimes. A good aggregate CAGR can still be fragile.

## 7.8 Bootstrap / resampling

Use dependence-aware block/stationary bootstrap rather than only IID daily shuffles. Present distributions/uncertainty, not false future guarantees.

## 7.9 Multiple testing

Every factor/model/portfolio/parameter trial remains counted within a `ResearchCampaign`. Failed trials cannot be deleted from the research lineage.

Support raw trial count and, where methodologically defensible, effective-trial estimates.

## 7.10 Statistical diagnostics

Strong V1 target includes Deflated Sharpe-style diagnostics and multiple-hypothesis correction (e.g. FDR) where appropriate. PBO/CSCV is an advanced validator/stretched V1 feature and must not delay the core pipeline.

P-values alone never promote a strategy.

## 7.11 Quant Critic verdicts

Deterministic validation produces hard statuses; the LLM critic interprets evidence.

Lifecycle verdicts:

- REJECTED
- RESEARCH_ONLY
- VALIDATED
- PAPER_CANDIDATE
- PAPER_VALIDATED / equivalent forward-evidence state

Hard failures such as detected temporal leakage are not overrideable by the LLM.

## 7.12 Strategy freeze before lockbox

Hash/freeze features, model/hyperparameters, portfolio, risk, execution, and code specification before locked-holdout evaluation. A post-holdout change creates a new candidate.

## 7.13 Red-team demonstrations

Flagship V1 must include:

1. look-ahead strategy with spectacular fake performance that is rejected,
2. random-strategy mining where multiple-testing risk is exposed,
3. high-turnover gross-alpha strategy whose edge disappears after realistic costs.

## 7.14 Validation result artifacts

Persist parameter surfaces, subperiod metrics, cost-sensitivity, bootstrap distributions, ablation results, trial ledger, lockbox state, critic inputs, and version metadata.

Validation must run offline on frozen datasets/artifacts.

---

# 8. Paper Trading and Forward Validation

## 8.1 Purpose

Paper trading collects true forward evidence after deployment. Historical backtests and paper trading share quant core semantics but differ in clock/data/broker adapters.

## 8.2 Shared code

Backtest and paper reuse:

- factor definitions,
- model inference,
- portfolio constructor,
- risk engine,
- order planner,
- domain order/fill/position objects,
- accounting,
- analytics.

Adapters differ:

```text
Backtest: HistoricalClock + FrozenData + SimulatedBroker
Paper:    RealClock       + LatestData + PaperBroker
```

## 8.3 Paper deployment

A `PAPER_CANDIDATE` becomes a versioned `PaperDeployment` referencing frozen strategy/model/portfolio/risk/execution/data-pipeline/application versions. Changes create a new deployment rather than mutating history.

## 8.4 Immutable predictions

Persist paper prediction snapshots before outcomes occur. They may be invalidated but not overwritten after the fact.

Tag predictions as shadow/active and link them later to realized outcomes for forward Rank IC.

## 8.5 EOD scheduler flow

```text
US session closes
  ↓
wait configured availability delay
  ↓
validate expected session/data freshness
  ↓
ingest latest bars + relevant filings
  ↓
publish PIT snapshot
  ↓
if rebalance date: factors → inference → portfolio → risk → orders
  ↓
next eligible session: paper execution
  ↓
reconciliation
  ↓
analytics / evidence
```

Non-rebalance days still mark positions, process actions, monitor health, and reconcile state.

## 8.6 Data gates

Stale market data, severe coverage gaps, invalid model artifact, broken risk engine, or failed reconciliation can halt new orders. A rebalance must not silently proceed on materially partial data.

## 8.7 Paper broker abstraction

Support an internal deterministic simulated paper broker first. External broker paper adapters may be added behind the same interface.

Internal ids remain canonical; external broker ids are mappings, not domain identities.

## 8.8 Idempotency and recovery

Each scheduled paper run has a deterministic/idempotent run key based on deployment and session. Duplicate scheduler delivery must not create duplicate orders.

Persistent state machine supports recovery after crashes. An uncertain external broker submission is reconciled before any retry.

## 8.9 Reconciliation

Compare QuantLab expected cash/positions/orders/fills with broker-reported state. Mismatches create incidents and may freeze new trading. Corrections use auditable reconciliation adjustments, not silent database edits.

## 8.10 Champion / challenger

One paper champion may drive the active paper portfolio. Challengers produce immutable forward predictions and shadow portfolios but do not submit active broker orders.

Promotion requires a proposal/evidence review; do not auto-promote a challenger because of short-sample outperformance.

## 8.11 Drift / divergence

Monitor:

- feature distribution drift,
- missingness drift,
- prediction/score dispersion drift,
- universe composition drift,
- forward predictive performance,
- backtest-vs-paper turnover/cost/execution divergence.

Distinguish data-pipeline drift from market/model drift.

## 8.12 Kill switch

States: ACTIVE / PAUSED / HALTED.

Automatic halts are for correctness/operational safety (stale data, duplicate-order risk, severe reconciliation mismatch, invalid model, risk-engine failure), not default reactions to ordinary performance drawdowns.

A halt blocks new orders; it does not automatically liquidate all positions.

## 8.13 Operational artifacts

Persist deployments, runs, predictions, orders, fills, positions, equity, reconciliations, incidents, drift reports, and promotion proposals.

## 8.14 Paper evidence maturity

Use evidence maturity based on calendar duration, prediction count, rebalance count, and independent decision periods. Do not call a strategy “proven.”

## 8.15 Paper tests

Critical: duplicate scheduler, restart after each state boundary, stale data, coverage failure, reconciliation mismatch, immutable predictions, deployment freeze, champion/challenger isolation, kill switch, secret redaction, and full month-end→fill→outcome forward simulation.

---

# 9. Agentic Research and MCP / Tool Architecture

## 9.1 Roles

Use three logical roles, not a swarm:

- Research Agent — proposes falsifiable hypotheses,
- Experiment Orchestrator — converts approved ideas into typed experiment specs and tool calls,
- Quant Critic — attacks conclusions using structured evidence.

These may share an underlying model with distinct contexts.

## 9.2 Research campaign

Every agentic research question is a versioned `ResearchCampaign` containing hypotheses, experiments, model trials, validation runs, critic reports, budgets, sources, and reports.

## 9.3 Hypothesis contract

A hypothesis contains:

- claim,
- plausible mechanism,
- expected evidence,
- falsification condition.

The system must allow the valid conclusion “no edge.”

## 9.4 ExperimentSpec boundary

Agents do not run arbitrary free-form “best strategy” requests. They emit a validated `ExperimentSpec` covering dataset, universe, alpha/features/model, portfolio, execution, validation, and compute/search budget.

Changing a configuration after observing results creates a new experiment id.

## 9.5 Budgeting

Campaigns cap hypotheses, experiments, model trials, compute time/concurrency, agent steps, LLM tokens/cost. Agents cannot expand their own budget.

## 9.6 Typed tools

Expose narrowly scoped tools such as:

- dataset/factor/model inspection,
- hypothesis/experiment creation,
- factor research,
- model training/evaluation,
- backtest,
- experiment comparison,
- robustness/ablation/cost stress,
- paper status inspection,
- grounded report generation.

Standard agents do not receive unrestricted shell, Python, SQL, database writes, result mutation, or direct broker-order submission.

## 9.7 Permission gateway

Before every tool execution:

```text
schema validation
  ↓
role permission
  ↓
campaign budget
  ↓
resource limits
  ↓
execution
```

Prompt text cannot elevate permissions.

## 9.8 MCP

MCP is an adapter over application services, not the Quant Core. Web, CLI, REST, MCP, and worker jobs share the same application service implementations and schemas.

## 9.9 Structured tool results

Tools return structured authoritative ids/metrics/warnings, not prose claims. LLMs narrate results but do not calculate authoritative metrics.

## 9.10 Grounded quantitative claims

Every quantitative claim in an agent-generated report must map to a deterministic metric/artifact. A claim verifier rejects unsupported numbers.

Reports distinguish FACT from INTERPRETATION.

## 9.11 Research memory hierarchy

- PostgreSQL structured memory is authoritative.
- Artifact store holds configs/reports/results.
- Semantic index is optional retrieval convenience.
- LLM context is temporary working memory.

Never use a vector store as the source of truth for performance metrics.

## 9.12 Duplicate research detection

Hash-identical experiments reuse or reference existing results. Similar-hypothesis retrieval can warn the agent without automatically blocking a genuinely distinct methodology.

## 9.13 Prompt/model/run registry

Version prompts, tool schemas, agent role version, provider/model, sampling settings, input/output hashes, tokens, latency, cost, and campaign association.

Provider SDKs sit behind `LLMProvider` adapters.

## 9.14 External text is untrusted

SEC filings, papers, webpages, and retrieved text are untrusted data. They cannot modify system permissions or operational policy. Prompt-injection resistance comes from tool/permission architecture, not only prompt wording.

## 9.15 Paper controls

Research agents cannot submit arbitrary broker orders. Higher-level deployment/pause/promotion controls belong to operator/policy roles and still flow through deterministic paper/risk services.

## 9.16 Research report

Report structure:

- question,
- hypothesis,
- methodology,
- dataset/data confidence,
- experiments conducted,
- evidence,
- robustness,
- failed/rejected variants,
- multiple-testing context,
- limitations,
- Quant Critic assessment,
- conclusion,
- next research question.

Do not hide rejected trials.

## 9.17 Agent tests

Must verify unauthorized-tool denial, budget enforcement, immutable authoritative results, malformed-spec rejection, duplicate detection, unsupported-claim rejection, lockbox restrictions, broker-order denial, prompt-injection non-escalation, crash/resume, step limits, and failed-experiment retention.

---

# 10. Application Layer, API, CLI, Dashboard, and Demo UX

## 10.1 UI responsibility

UI explores, triggers, and explains. It does not independently calculate quantitative truth. Metrics/verdicts come from backend artifacts.

## 10.2 Interfaces

- FastAPI application API,
- Typer-style CLI,
- Next.js/TypeScript research web app,
- MCP adapter,
- optional notebooks for exploratory research only.

## 10.3 Dashboard information architecture

Main navigation:

```text
Overview
Research
  Campaigns
  Hypotheses
  Experiments
  Factors
  Models
Strategies
  Backtests
  Validation
  Compare
Forward
  Paper Trading
  Champion / Challenger
  Incidents
System
  Data
  Agent Runs
  System Health
```

## 10.4 Research campaign workspace

Primary UX shows hypothesis, falsification criteria, research progress, experiment lineage, evidence, budget consumption, and Quant Critic output. The workspace is artifact-centric; chat is secondary.

## 10.5 Experiment page

Tabs:

- Overview
- Performance
- Factors
- Portfolio
- Execution
- Robustness
- Data
- Audit

Metrics include definitions, assumptions, and calculator/version provenance.

## 10.6 Key visualizations

- equity curve vs benchmark,
- drawdown/underwater curve,
- Rank IC/factor decay,
- factor correlation heatmap,
- walk-forward folds,
- portfolio sector/factor exposure,
- parameter stability heatmap,
- cost sensitivity/break-even curve,
- bootstrap distributions,
- multiple-testing/trial context,
- backtest-paper divergence,
- champion/challenger forward comparison.

## 10.7 Decision trace

For any holding/trade, support a lineage view:

```text
Dataset → Feature/Factor Snapshot → Model Score/Rank → Portfolio Reason → Risk → Order → Fill
```

## 10.8 Strategy Evidence Card

A concise evidence object should summarize performance, data confidence, OOS/lockbox status, parameter stability, cost robustness, trial count, forward-evidence maturity, and main concern. Raw underlying metrics remain accessible.

## 10.9 Data/system health pages

Show freshness, coverage, confidence/bias flags, latest successful ingestions/runs, workers/scheduler/database health, incidents, and paper readiness.

## 10.10 Long-running jobs

Backtests/training/validation use asynchronous persisted jobs. API returns a job id; UI shows explicit phase/progress rather than hanging a request.

## 10.11 Demo mode

Public recruiter/demo mode uses frozen datasets/artifacts only, is read-only, and cannot reach paper credentials or operational controls.

Flagship public demos:

1. “Does Quality Improve Momentum?” end-to-end research story.
2. ETF tactical-allocation secondary example.
3. Backtest Red Team: look-ahead, random mining, and cost illusion.

## 10.12 UI style

Modern research workstation, dark-first with light support, restrained visual semantics, not a neon crypto-trading dashboard. Optimize for clarity/auditability over decorative animation.

## 10.13 API boundaries/security

Frontend never queries databases directly. Authorization is enforced in backend application services, not by hiding buttons.

---

# 11. Infrastructure, DevOps, Observability, and Security

## 11.1 V1 deployment shape

Local-first, containerized, production-shaped modular monolith. No Kubernetes requirement.

Core services:

- API,
- web,
- worker,
- scheduler,
- MCP,
- PostgreSQL,
- optional observability profile.

Use separate workers/queues/priorities where needed so heavy research cannot block paper-critical jobs.

## 11.2 Storage roles

- PostgreSQL: transactional state and metadata.
- Parquet: analytical/time-series datasets and large artifacts.
- DuckDB: analytical query engine over Parquet.
- Artifact store: models, reports, configs, validation outputs; local filesystem first, S3-compatible abstraction later.

## 11.3 Persistent job model

Heavy work is a persisted job with type, status, payload, result reference, retries, worker id, timing, error, and idempotency key. API processes do not run long quant jobs inline.

## 11.4 Scheduler

Scheduler decides when jobs should exist. Workers execute them. Schedule/job state is persistent and recoverable after restart.

## 11.5 Dataset publication

Dataset builds pass through BUILDING/VALIDATING/PUBLISHED or equivalent states. Quant engines may read only published datasets. Avoid half-built data visibility.

## 11.6 Artifact immutability and integrity

Authoritative experiment/model/report artifacts are immutable/versioned and hashed. Re-runs create new ids or exactly matching content references; they do not silently overwrite history.

## 11.7 Environment/code provenance

Record Python version, dependency-lock hash, container/build version, Git SHA, dirty-worktree indicator or code fingerprint, QuantLab version, and relevant engine/calculator versions.

## 11.8 Developer UX

`quantlab doctor` checks environment, PostgreSQL, artifact storage, DuckDB, calendar, data paths, required keys, and optional broker configuration.

## 11.9 Logging/audit

Use structured logs with correlation ids and domain ids. Separate operational logging from durable audit events such as lockbox openings, paper promotions/pauses, risk-config changes, and reconciliation adjustments.

## 11.10 Metrics/tracing

Track API/job latency/failures, queue depth, data freshness/coverage, backtest/training duration, paper-run/reconciliation failures, active deployments, and agent tokens/cost. OpenTelemetry/Prometheus-compatible interfaces are acceptable without requiring a full stack in default development.

## 11.11 Health/readiness

Provide liveness/readiness and deeper paper-readiness checks covering database, calendar, latest dataset, broker, risk engine, and scheduler.

## 11.12 CI/CD

Pull-request pipeline:

```text
lint/format
→ type checks
→ unit/property tests
→ quant correctness
→ integration/golden tests
→ security checks
→ build
```

Core correctness CI is offline and uses frozen fixtures.

Paper runtime deployment has stricter gates than web/demo deployment.

## 11.13 Backups and integrity

Back up PostgreSQL, dataset manifests/configs, important artifacts/models, and reproducibility-critical raw/normalized snapshots. Periodically verify restore/integrity rather than assuming backups work.

## 11.14 Security boundaries

Roles/concepts: public demo, researcher, operator, admin.

- secrets never committed/logged,
- use a `SecretProvider` abstraction,
- databases are not publicly exposed,
- public demo is read-only/rate-limited,
- heavy writes are authenticated/budgeted,
- validate all API/MCP/CLI/agent-tool inputs,
- no raw agent SQL/shell,
- safe artifact ids instead of arbitrary filesystem paths,
- avoid unsafe deserialization of untrusted model artifacts.

## 11.15 Recovery scenarios

Design and test recovery from:

- worker crash during ingestion/backtest,
- duplicate job delivery,
- crash after order creation/submission,
- uncertain broker response,
- partial dataset build,
- database/app restart.

Paper jobs have priority over batch research where resources conflict.

---

# 12. Testing Strategy and Quality Gates

## 12.1 Test layers

1. Static/contracts.
2. Unit tests.
3. Property-based tests.
4. Quant correctness tests.
5. Metamorphic tests.
6. Integration tests.
7. Golden/regression tests.
8. Red-team/fault-injection tests.
9. Critical end-to-end workflow tests.

Quant correctness takes precedence over maximizing code-coverage percentage.

## 12.2 Architecture tests

Automate dependency-boundary checks. Core/domain must not drift toward UI/LLM/provider/database dependencies.

## 12.3 Data critical tests

- OHLC integrity,
- uniqueness,
- PIT filing availability,
- restatements,
- historical universe membership,
- corporate actions,
- data-quality thresholds.

## 12.4 Factor tests

Formula correctness, direction, missingness, staleness, winsorization/ranking, split/dividend consistency, and no label/future access.

## 12.5 ML critical tests

Temporal ordering, purge/embargo, train-only fitted transforms, ranking groups, label isolation, out-of-sample enforcement, label shuffle, synthetic signal, and deterministic seeds where supported.

## 12.6 Portfolio/accounting property tests

Randomly generate scores/sectors/weights/constraints and verify long-only, caps, exposure, cash, deterministic selection, conflict handling, accounting conservation, and no impossible positions.

## 12.7 Backtest critical tests

- signal-close cannot fill same close,
- gaps fill at correct next-session semantics,
- missing opens do not fabricate fills,
- split/dividend/symbol change correctness,
- buy/sell round-trip accounting,
- cost reconciliation,
- deterministic replay,
- event ordering.

## 12.8 Metamorphic tests

Examples:

- price-scale invariance where economics are unchanged,
- capital-scale invariance when impact is disabled,
- ticker-rename invariance,
- split invariance,
- input-row-order invariance,
- cache/parallelism invariance,
- old dataset results unaffected by creation of newer datasets.

## 12.9 Golden fixtures

Maintain:

- a human-computable synthetic multi-month dataset,
- a small event-by-event golden backtest,
- a frozen real-market slice for regression.

Golden expected outputs are not auto-updated just to make tests pass.

## 12.10 Validation tests

Synthetic stable edge, pure noise, overfit spike, cost-fragile, execution-delay-fragile, multiple-testing, and holdout-isolation scenarios.

## 12.11 Agent/security tests

Unauthorized tool, budget overflow, result tampering, unsupported metric claim, failed-experiment retention, prompt injection, lockbox restriction, broker-order denial, crash resume, and max-step termination.

Use a deterministic fake LLM provider for normal CI. Real-model evals are separate.

## 12.12 Paper tests

Scheduler idempotency, crash recovery across state transitions, reconciliation mismatch, kill switch, challenger isolation, immutable predictions, stale-data gate, and secret leakage.

## 12.13 Fault injection

Simulate provider timeout, DB outage, disk/resource failure where practical, worker termination, duplicate callback, malformed/stale market data, missing model artifact, and broker timeout.

## 12.14 Quality gates

A milestone/release is not complete until:

- specified tests pass,
- docs/contracts are updated,
- no unresolved critical/high correctness issues remain,
- schema migrations exist where needed,
- deliberate quant behavior changes are documented.

All discovered correctness bugs must add regression tests.

## 12.15 Bug severity

Critical: look-ahead/future data, wrong PnL/accounting, duplicate operational orders, holdout leakage.

High: wrong factor ranking, wrong constraints, severe reconciliation failures.

Medium: non-critical report/API errors.

Low: polish.

Critical/high block releases.

---

# 13. V1 Build Order, Milestones, and Acceptance Criteria

## M0 — Engineering Foundation

### Deliver

- monorepo/package skeleton,
- domain contracts,
- config/logging/error foundations,
- PostgreSQL / Parquet / DuckDB plumbing,
- artifact store abstraction,
- CI/lint/type/test setup,
- Docker Compose,
- frozen synthetic fixtures,
- `quantlab doctor`.

### Acceptance

- environment starts reproducibly,
- CI runs offline,
- architecture boundaries pass,
- no LLM/dashboard/strategy work is required yet.

---

## M1 — Point-in-Time Data

### Deliver

- instrument master/symbol history,
- provider abstractions/adapters,
- immutable raw snapshots,
- normalized market/fundamental/action/macro data,
- PIT fundamental queries,
- historical listing snapshots,
- `US_LIQUID_1000`,
- dataset manifests/hashes,
- quality/confidence/bias reporting.

### Acceptance

System can answer historical universe and historical-known-fundamental questions correctly. Restatement, universe, OHLC, symbol, and corporate-action tests pass. Produce immutable `DATASET-v001` or equivalent.

Do not proceed while PIT critical tests fail.

---

## M2 — Factor Research

### Deliver

V1 factors, transforms, registry, snapshots, Rank IC, quantiles, decay, turnover, correlations, coverage, and deterministic simple multi-factor baseline.

### Acceptance

A CLI/application command can research a factor and reproduce its results from a dataset id. Simple baseline works without ML.

---

## M3 — Portfolio + Event-Driven Backtest

### Deliver

Top-K/buffer selection, equal-weight baseline, risk constraints, order planner, simulation clock/events, broker simulator, execution/cost models, accounting ledgers, analytics, audit trail.

### Acceptance

Run the baseline strategy through a multi-year authoritative backtest with orders/fills/cash/positions/equity and pass next-open, accounting, split/dividend, symbol-change, and deterministic-replay tests.

At M3 QuantLab must already be a useful deterministic quant/backtesting platform without AI.

---

## M4 — Validation and Falsification

### Deliver

Research/validation/lockbox partitioning, robustness suites, cost/execution/universe/Top-K sensitivity, ablation, bootstrap, trial ledger, multiple-testing diagnostics, critic input artifacts.

### Acceptance

The three flagship red-team strategies are correctly identified as invalid/fragile. Validation emits deterministic lifecycle verdicts. Lockbox isolation and trial retention pass.

---

## M5 — ML Ranking

### Deliver

PIT panel builder, labels aligned to executable timing, purged walk-forward splits, Ridge, LightGBM ranker, model registry, OOS prediction snapshots, comparison to simple baseline.

### Acceptance

Composite vs Ridge vs LightGBM is evaluated on OOS evidence only. ML is allowed to lose; milestone success is methodological correctness, not ML superiority.

---

## M6 — Paper Trading and Forward Evidence

### Deliver

Versioned paper deployments, scheduler/jobs, latest-data gates, internal paper broker, immutable predictions, fills/accounting/reconciliation, champion/challenger shadow mode, drift/divergence monitoring, incidents, kill switch.

### Acceptance

Month-end→next-session→outcome flow works under a simulated real clock. Scheduler idempotency, crash recovery, reconciliation mismatch, prediction immutability, challenger isolation, and kill-switch tests pass.

---

## M7 — Agentic Research + MCP

### Deliver

Campaigns/hypotheses, typed ExperimentSpec, budgets, Research/Experiment/Critic roles, tool registry/permissions, run/prompt registry, claim grounding/verifier, MCP adapter.

### Acceptance

A user question such as “Does quality improve momentum?” can produce hypothesis→experiments→comparison→ablation→validation→critic→grounded report without agents inventing metrics, deleting failed trials, exceeding budget, opening holdouts improperly, or submitting direct broker orders.

---

## M8 — API, CLI, and Research Dashboard

### Deliver

FastAPI application layer, persistent async jobs, first-class CLI, Next.js research workstation, campaign/experiment/factor/model/validation/paper/data/system views, evidence cards, decision traces, public frozen demo mode.

### Acceptance

A new user can answer what was researched, which data/model was used, whether OOS/lockbox passed, what was tried, how cost/parameter sensitive it is, what paper evidence exists, and where every important metric came from without reading source code.

---

## M9 — Flagship Release

### Deliver

Hardening, docs/ADRs, performance tuning, demo reliability, architecture/case-study pages, reproducible install/run instructions, CI/release gates, and three public demonstrations.

### Acceptance

Full system acceptance workflow runs on frozen data offline:

```text
PIT Dataset
 → Universe
 → Factors
 → Baseline + ML Challenger
 → Portfolio
 → Authoritative Backtest
 → Validation
 → Paper Candidate
 → Simulated Forward Sessions
 → Agent Campaign
 → Grounded Report
```

All quant-critical tests pass.

---

# 14. Codex Implementation Guardrails

These rules are part of the design, not optional developer preferences.

1. **Do not advance milestones until current acceptance tests pass.**
2. **Do not claim completion without test evidence.**
3. **Do not build the full dashboard before M8.**
4. **Do not build autonomous research agents before M7.**
5. **Do not optimize for the highest CAGR/Sharpe. Optimize for correctness, evidence, and reproducibility.**
6. **Do not use LLM reasoning for authoritative numerical results or safety constraints.**
7. **Do not silently introduce new asset classes, frameworks, infrastructure, or strategy families.**
8. **Do not mutate historical results/artifacts. Version them.**
9. **Do not update golden expected results solely to clear a failure. Explain and document the intended behavioral change first.**
10. **Do not call network providers inside authoritative historical backtests/validation.**
11. **Do not let provider-specific APIs leak across core boundaries.**
12. **Do not bypass point-in-time access even when the current database already contains future/restated values.**
13. **Do not permit TRAIN predictions in authoritative ML portfolio evaluation.**
14. **Do not let a revised candidate reuse a consumed holdout as unseen data.**
15. **Do not let research agents submit arbitrary paper orders or access secrets.**

---

# 15. Initial Technology Choices

These are defaults, not excuses to couple the domain to implementations.

- Python 3.12+
- NumPy
- Polars as primary dataframe engine; Pandas where ecosystem compatibility requires it
- PyArrow / Parquet
- DuckDB
- PostgreSQL
- SQLAlchemy or SQLModel-style persistence layer
- SciPy / statsmodels
- scikit-learn
- LightGBM
- XGBoost optional, not required for V1
- cvxpy available for later constrained optimization, not default baseline
- FastAPI
- Pydantic
- Typer
- Next.js + TypeScript
- TanStack Query
- Plotly or another research-suitable chart library
- pytest
- Hypothesis property testing
- Ruff
- mypy
- pre-commit
- Docker / Docker Compose
- GitHub Actions or equivalent CI

Agent framework is adapter-level. Do not couple Quant Core to LangChain/LangGraph/OpenClaw/Hermes or a single LLM provider.

---

# 16. Flagship Research Case

Primary case study:

> **Does adding quality to momentum improve out-of-sample risk-adjusted performance in liquid US equities?**

Expected research path:

```text
Momentum baseline
  ↓
Independent quality factor studies
  ↓
Momentum + Quality composite
  ↓
Incremental IC / quantile evidence
  ↓
Ablation
  ↓
Top-30 portfolio
  ↓
Authoritative cost-aware backtest
  ↓
Parameter / cost / subperiod robustness
  ↓
Locked holdout
  ↓
Paper candidate
  ↓
Champion/challenger forward comparison
```

ML is a challenger to this simple scientific baseline, not the product's justification.

---

# 17. Definition of V1 Success

QuantLab V1 is complete when it can demonstrate all of the following:

1. Historical data access is point-in-time aware and data limitations are explicit.
2. Factor research provides IC/quantile/decay/stability evidence.
3. Portfolio/risk/order construction is deterministic and constrained.
4. Authoritative backtests use executable timing and correct accounting.
5. Robustness tooling attempts to falsify attractive results before promotion.
6. ML is evaluated with purged temporal OOS methodology against simple baselines.
7. Paper trading creates immutable forward evidence and survives operational failures safely.
8. Agentic research uses typed tools, budgets, permissions, and grounded claims.
9. Public/demo UX can trace conclusions to datasets, experiments, artifacts, and code versions.
10. The complete frozen-data acceptance workflow runs offline and reproducibly.

The product does **not** need a profitable production strategy to meet V1 success. Discovering that a complex model adds no robust value is a valid and valuable scientific result.

---

# 18. Handoff Sequence

This master specification is the source design document.

The implementation workflow is:

```text
Master Design Spec
  ↓ human review
Approved Written Spec
  ↓
Detailed Implementation Plan
  ↓
Milestone-by-Milestone Execution
  ↓
Verification at Every Gate
```

The next artifact after approval of this written specification must be a detailed implementation plan. Implementation must not begin before that plan is reviewed enough to remove ambiguity around milestone sequencing, test-first slices, and commit checkpoints.

---

## Implementation note (added after the build)

This document is the **design as proposed**, kept as written. Several choices in it were
not carried into the implementation, and the differences are deliberate rather than
oversights:

| Proposed here | What was built | Why |
|---|---|---|
| PostgreSQL for transactional metadata | SQLite | Nothing in V1 needs concurrent writers or a server process. SQLite keeps the whole system runnable from a clone with no infrastructure. |
| Parquet files queried by DuckDB | JSON partitions read directly, SQLite for ad-hoc SQL | Partitions are small and read whole. Adding a columnar engine would buy nothing measurable and add a heavy dependency to a project whose selling point is that its numbers are traceable to its own code. |
| NumPy, SciPy, statsmodels, scikit-learn, LightGBM | All statistics, linear algebra, and the tree learner implemented in-repo | Same reason: every number the engine reports can be traced to code in this repository. The cost is speed, and that cost is real - a thirty-year study takes minutes. |
| Polars / PyArrow | Standard library | Not needed at this data size. |
| Typer for the CLI | argparse | One less dependency for the same surface. |
| TanStack Query, Plotly | Plain fetch, inline SVG | The dashboard reads a handful of static artifacts; a query cache and a charting library would be more machinery than the job needs. |

FastAPI, Pydantic, Next.js, TypeScript, pytest, Hypothesis, Ruff, mypy, and the MCP
adapter layer were all built as specified.

The point-in-time semantics, factor evaluation requirements, walk-forward discipline,
falsification ladder, and paper-operations design in this document were followed. Where
the implementation departs from the spec on those, it is documented in
`docs/architecture/` and `docs/calculators/`.
