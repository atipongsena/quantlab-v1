# QuantLab V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Status:** Approved for execution on 2026-08-16. QuantLab implementation has not started.

**Selected Workflow:** Superpowers Subagent-Driven Development, executed one milestone at a time with one implementation agent at a time, independent task review, milestone gate review, and final whole-branch review.

**Goal:** Build QuantLab V1 as a reproducible, point-in-time-correct research, authoritative backtest, validation, paper-forward-test, and constrained agentic-research platform for US equities and ETFs.

**Architecture:** Implement a Python 3.12+ modular monolith whose dependency direction is adapters/apps → application services → quant modules → domain. PostgreSQL owns transactional metadata, Parquet owns analytical data, DuckDB queries Parquet, and immutable hashed artifacts carry authoritative outputs. Deterministic code is the sole authority for timing, factors, labels, portfolio/risk, execution, accounting, metrics, validation, and paper safeguards; agents and UI only orchestrate and explain typed results.

**Tech Stack:** Python 3.12+, NumPy, Polars, PyArrow/Parquet, DuckDB, PostgreSQL, SQLAlchemy 2.x, SciPy, statsmodels, scikit-learn, LightGBM, FastAPI, Pydantic 2.x, Typer, pytest, Hypothesis, Ruff, mypy, Docker Compose, Next.js + TypeScript, TanStack Query, Plotly, and an adapter-level LLM/MCP integration.

## Global Constraints

- Source of truth: docs/superpowers/specs/2026-08-16-quantlab-v1-design.md. If this plan and the approved spec disagree, stop and amend the plan before code.
- Locked V1 scope: US equities + ETFs; Daily/EOD; monthly equity rebalance; free-first data; long-only cash account; no leverage or shorting; Top-30 equal-weight baseline with entry/hold buffer; SPY total-return benchmark.
- Build sequence is strict: M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9.
- A milestone is complete only after its gate command exits 0 and writes artifacts/milestone-gates/MN.json with status PASS, the current Git SHA, command results, and artifact hashes.
- scripts/verify_milestone.py MN --require-prior must fail when any prior gate is missing, not PASS, does not reference an ancestor acceptance commit, or its protected-file/evidence hashes no longer match. A later milestone may not add a bypass flag.
- M0–M6 may not add LLM SDKs, apps/web, apps/mcp, quantlab/agents, or agent framework dependencies. M7 may add agent/MCP code but no web dashboard. apps/web begins only in M8.
- Authoritative historical backtests and validation run offline on a PUBLISHED frozen dataset and must fail on attempted network access.
- A datum is usable only when available_at <= decision_time. No query path may substitute period end, ingestion time, or latest-known value for available_at.
- Signals created after EOD may not fill at the same close. Default execution is the next eligible session open plus explicit adverse slippage and costs.
- Feature/factor runtime cannot import labels. Authoritative ML portfolio evaluation rejects TRAIN predictions; only VALIDATION or TEST predictions may enter.
- Consumed holdouts remain consumed. Any post-holdout strategy/code/config change creates a new candidate and cannot relabel that holdout unseen.
- Golden expected outputs are changed only after a failing regression is explained in docs/changes/quant-behavior/, independently recomputed, reviewed, and approved. Never regenerate expected files from the implementation under test.
- Random seeds, calendar/timezone, sort keys, floating-point tolerances, dependency lock hash, code fingerprint, and engine/calculator versions must be explicit in authoritative artifacts.
- LLM output is never accepted as a metric, portfolio/risk decision, validation verdict, order, fill, accounting entry, dataset value, or authoritative artifact mutation.
- Do not add live money, intraday/tick/HFT, derivatives, FX, crypto, shorting, leverage, RL, deep price models, alternative data, paid institutional-data dependence, 100+ factors, agent swarms, Kubernetes, Spark, enterprise multi-tenancy, or full tax accounting.
- PBO/CSCV, external paper brokers, advanced market impact, S3, semantic memory, SHAP-heavy analysis, Prometheus/Grafana, and advanced optimizers are non-blocking stretch work and are excluded from the critical path.

---

## Approved Execution Method

Subagent-Driven Development is selected instead of inline execution because this plan has 51 reviewable tasks, high-risk quant correctness boundaries, and available multi-agent support. The controller preserves cross-milestone context while fresh implementers and reviewers reduce context contamination and confirmation bias.

Execution controls:

1. Do not start code from this approval turn. Begin only after an explicit instruction to start M0.
2. Before Task M0.1, use superpowers:using-git-worktrees. Because the handoff directory is not yet a Git repository, the execution preflight must initialize or place it in a Git repository, create a documentation-only baseline commit, and create/verify an isolated feature worktree. Never implement directly on main/master.
3. Execute milestones sequentially. Within a milestone, continue task-by-task without routine check-ins; stop only for a genuine blocker, a plan/spec conflict, or a failed gate that cannot be resolved safely.
4. Never run two implementation agents concurrently. A reviewer runs only after the implementer has produced a committed diff and report.
5. Use a persistent Superpowers SDD ledger keyed to this plan. It records task briefs, commits, tests, review verdicts, fix rounds, deferred minors, gate evidence, and the next uncompleted task.
6. Split a parent task into child briefs before dispatch when it references more than eight implementation/test paths, crosses more than one service boundary, or cannot fit one coherent red-green-review cycle. Child briefs may narrow files but may not weaken, omit, or reinterpret the parent's interfaces, tests, acceptance criteria, scope controls, or gate. Record the split in the ledger; the parent is complete only when every child review is clean. Child commit messages use the parent's checkpoint message plus “part N: scope”.
7. Run independent spec-compliance and code-quality review after every parent/child task. Critical or Important findings enter the bounded fix/re-review loop; no milestone advances with an unresolved load-bearing finding.
8. After each milestone's test commands pass, perform one broad milestone diff review before writing the PASS gate artifact. M9 also receives the required whole-branch final review.
9. Specify models explicitly for every dispatch: gpt-5.6-luna high for mechanical documentation/configuration work; gpt-5.6-terra high for ordinary multi-file implementation and routine review; gpt-5.6-sol high for PIT data, temporal leakage, portfolio/accounting, backtest, validation, paper recovery, and security work; gpt-5.6-sol xhigh for milestone-wide quant-critical reviews and the final whole-branch review.
10. If the selected workflow becomes unavailable, stop and obtain approval before falling back to inline executing-plans. Do not silently change the review model or remove per-task reviews.

## Execution Protocol

### Required read order before implementation

1. CODEX_HANDOFF.md
2. docs/superpowers/specs/2026-08-16-quantlab-v1-design.md
3. This plan
4. The nearest AGENTS.md present in the implementation repository

### Standard red-green-refactor loop for every task

- [ ] Add the named test files and exact test cases listed in the task.
- [ ] Run the task's narrow command and confirm it fails for the intended missing behavior, not an import/setup error.
- [ ] Implement only the files and public interfaces listed for the task.
- [ ] Run the narrow command until it passes; then run the milestone regression command.
- [ ] Inspect git diff --check and git status --short; stage only task-owned files.
- [ ] Commit with the checkpoint message shown in the task. Do not combine checkpoints across a failing milestone gate.

### Command conventions

Run from repository root in the Python 3.12 environment created by M0. Within a task, “run the named tests” means the exact command python -m pytest -q followed by every test path listed in that task's Files block, in listed order; it does not permit selecting a smaller subset.

~~~bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy quantlab apps
python -m pytest -q
~~~

Commands tagged offline run with QUANTLAB_OFFLINE=1 and tests/socket_guard.py blocking non-loopback sockets. Commands tagged services require docker compose up -d postgres.

### Milestone gate protocol

For milestone MN:

~~~bash
python scripts/verify_milestone.py MN --require-prior
git diff --check
git status --short
~~~

Expected: verifier exits 0; the gate JSON is PASS and contains the exact verification command list, exit codes, Git SHA, dirty flag false, dependency-lock hash, fixture/dataset ids, and hashes of authoritative outputs. Commit the gate artifact with message chore(gate): accept MN only after reviewing those fields. The gate verifier must refuse to write PASS for a dirty worktree.

## Target Repository Map

Each file has one responsibility. Do not collapse these boundaries into a single service or utility module.

~~~text
apps/
  api/                    FastAPI composition and HTTP schemas (M8)
  cli/                    Typer composition; no quant calculations
  mcp/                    MCP adapter over application tools (M7)
  worker/                 persisted-job execution
  scheduler/              schedule creation only
  web/                    Next.js research workstation (M8)
quantlab/
  domain/                 dependency-free frozen entities, enums, protocols
  common/                 config, ids, hashing, clocks, errors, logging
  infrastructure/         SQLAlchemy, Parquet/DuckDB, artifacts, jobs, secrets
  data/                    providers, raw capture, normalization, PIT queries, publication
  universe/               historical listings and US_LIQUID_1000
  factors/                definitions, transforms, registry, evaluation, composites
  portfolio/              selection, weighting, constraints, risk, order planning
  backtest/               events, simulation engine, broker, execution, ledgers
  analytics/              versioned calculators and benchmark-relative metrics
  validation/             partitions, lockbox, robustness, trials, verdicts
  ml/                     labels, panels, splits, models, predictions, registry
  paper/                  deployment, scheduler flow, broker, reconciliation, evidence
  research/               campaigns, hypotheses, ExperimentSpec, reports
  agents/                 adapters, roles, permissions, claim grounding (M7)
configs/                  versioned defaults, milestones, universes, strategies, validation
data/fixtures/            reviewed synthetic and frozen real-market inputs
artifacts/golden/         human-derived immutable expected outputs
tests/                    mirrors package plus architecture, integration, e2e, red-team
scripts/                  gate, fixture-integrity, offline, and release verification
docs/                     ADRs, contracts, calculators, runbooks, research cases
~~~

## Cross-Milestone Interface Ledger

The implementation may refine internals, but changing these public contracts requires a plan amendment before dependent work continues.

~~~python
InstrumentId = UUID
DatasetId = str
ExperimentId = str
ArtifactId = str

@dataclass(frozen=True, slots=True)
class TimePoint:
    value: datetime  # timezone-aware UTC

class PointInTimeData(Protocol):
    def price(self, instrument_id: InstrumentId, session: date, as_of: TimePoint, semantic: PriceSemantic) -> MarketBar: ...
    def fundamental(self, instrument_id: InstrumentId, metric: str, as_of: TimePoint) -> FundamentalObservation | None: ...
    def universe(self, universe_id: str, session: date, as_of: TimePoint) -> UniverseSnapshot: ...

class Factor(Protocol):
    definition: FactorDefinition
    def compute(self, context: FactorContext) -> FactorSnapshot: ...

class PortfolioConstructor(Protocol):
    def construct(self, request: ConstructionRequest) -> TargetPortfolio: ...

class Broker(Protocol):
    def submit(self, order: Order, market: MarketSnapshot) -> tuple[Order, tuple[Fill, ...]]: ...

class ValidationRunner(Protocol):
    def run(self, candidate: FrozenCandidate, spec: ValidationSpec) -> ValidationResult: ...

class RankingModel(Protocol):
    def fit(self, training: TrainingPanel) -> ModelArtifact: ...
    def predict(self, panel: InferencePanel, artifact: ModelArtifact, split: PredictionSplit) -> PredictionSnapshot: ...

class PaperBroker(Protocol):
    def submit_once(self, command: PaperOrderCommand) -> PaperSubmissionResult: ...
    def reconcile(self, deployment_id: str, session: date) -> ReconciliationResult: ...
~~~

## Dependency Graph and Release Gates

~~~text
M0 contracts/storage/test discipline
 └─ M1 PIT dataset
     └─ M2 deterministic factors
         └─ M3 portfolio + authoritative backtest
             └─ M4 validation/lockbox
                 └─ M5 ML challenger
                     └─ M6 paper forward evidence
                         └─ M7 constrained agent/MCP
                             └─ M8 API/CLI/web
                                 └─ M9 frozen flagship release
~~~

# M0 — Engineering Foundation

## Task M0.1: Packaging, quality tools, and enforceable milestone gates

**Files:** Create pyproject.toml, requirements.lock, .python-version, .gitignore, .pre-commit-config.yaml, configs/milestones.yaml, scripts/verify_milestone.py, scripts/check_scope.py, tests/test_milestone_gates.py, tests/test_scope_guard.py, tests/socket_guard.py, .github/workflows/ci.yml, quantlab/__init__.py, and package initializers only for apps/cli, apps/worker, apps/scheduler, quantlab/domain, quantlab/common, quantlab/infrastructure, and quantlab/application. Later tasks create their own package initializers when their milestone begins.

**Interfaces:** Produce CLI script quantlab = apps.cli.main:app; verify_milestone(milestone: str, require_prior: bool) -> GateReport. GateReport is a frozen domain-neutral record containing status, commands, exit codes, Git SHA, dirty flag, dependency hash, artifact hashes, and prior gates.

- [ ] Add tests named test_gate_rejects_missing_prior, test_gate_rejects_dirty_tree, test_gate_rejects_failed_command, test_gate_hashes_evidence, test_scope_rejects_premature_packages, test_scope_rejects_forbidden_v1_features, and test_socket_guard_blocks_external_network.
- [ ] Run python -m pytest tests/test_milestone_gates.py -q; expected failure is missing gate implementation.
- [ ] Add minimal packaging, quality configuration, offline socket guard, and verifier. configs/milestones.yaml must enumerate M0–M9 in order and list exact per-gate commands.
- [ ] Run python -m pytest tests/test_milestone_gates.py -q, python -m ruff check ., and python -m mypy quantlab apps; expected all pass.
- [ ] Commit: chore: establish QuantLab quality and milestone gates

## Task M0.2: Domain contracts and architecture boundaries

**Files:** Create quantlab/domain/identity.py, market.py, corporate_actions.py, signals.py, portfolio.py, orders.py, experiments.py, datasets.py, validation.py, paper.py; tests/domain/test_entities.py; tests/architecture/test_dependencies.py; docs/architecture/dependency-rules.md.

**Interfaces:** Implement the frozen entities named in the master spec with Decimal for money/quantity where accounting precision matters, timezone-aware timestamps, InstrumentId identity, and explicit enums. Domain imports are restricted to Python standard library and quantlab.domain.

- [ ] Add tests test_market_bar_rejects_naive_timestamp, test_symbol_change_preserves_instrument_id, test_order_state_transition_table, test_money_rejects_float, and test_domain_has_no_forbidden_imports.
- [ ] Run python -m pytest tests/domain tests/architecture -q; expected failure is missing entities and import rules.
- [ ] Implement the minimum immutable contracts and an AST-based dependency test forbidding FastAPI, Pydantic, SQLAlchemy, provider, LLM, MCP, and UI imports from quantlab/domain.
- [ ] Run python -m pytest tests/domain tests/architecture -q; expected all pass.
- [ ] Commit: feat(domain): define immutable QuantLab contracts

## Task M0.3: Configuration, deterministic ids/hashing, clocks, errors, and logging

**Files:** Create quantlab/common/config.py, ids.py, hashing.py, clock.py, errors.py, logging.py; configs/base.yaml, configs/test.yaml; tests/common/test_config.py, test_hashing.py, test_clock.py, test_logging.py.

**Interfaces:** load_config(paths: Sequence[Path], env: Mapping[str, str]) -> AppConfig; canonical_hash(value: JsonValue) -> str; Clock.now() -> TimePoint; DeterministicIdFactory.from_parts(namespace: str, parts: Sequence[str]) -> str.

- [ ] Test config precedence, secret redaction, canonical hash independence from mapping/input row order, frozen-clock behavior, UTC enforcement, and correlation/domain ids in structured logs.
- [ ] Run python -m pytest tests/common -q; expected failure is missing modules.
- [ ] Implement typed immutable config and deterministic primitives; do not read wall-clock time inside domain/quant modules.
- [ ] Run python -m pytest tests/common -q; expected all pass.
- [ ] Commit: feat(core): add deterministic configuration and provenance primitives

## Task M0.4: PostgreSQL, Parquet/DuckDB, artifact store, and persisted jobs

**Files:** Create docker-compose.yml, quantlab/infrastructure/db.py, models.py, repositories.py, parquet.py, duckdb.py, artifacts.py, jobs.py, migrations/env.py, migrations/versions/0001_foundation.py; tests/infrastructure/test_artifacts.py, test_parquet_duckdb.py, test_jobs.py, test_postgres.py.

**Interfaces:** ArtifactStore.put_bytes(kind, payload, metadata) -> ArtifactRef and get_verified(ref) -> bytes; AnalyticalStore.write_partition(dataset_id, table, frame) -> PartitionRef and query(sql, refs) -> pl.DataFrame; JobRepository.create_once(type, idempotency_key, payload) -> JobRecord.

- [ ] Test artifact immutability/content-addressing/path traversal rejection, Parquet round-trip/schema preservation, DuckDB read-only queries, job idempotency, and PostgreSQL migration round-trip.
- [ ] Run offline unit tests first; expected failure is missing stores. Start docker compose up -d postgres only for test_postgres.py.
- [ ] Implement local-filesystem ArtifactStore behind a protocol, transactional SQLAlchemy repositories, and publication-safe analytical writes.
- [ ] Run python -m pytest tests/infrastructure -q; expected all pass with services available and network blocked except loopback.
- [ ] Commit: feat(infra): add transactional and analytical storage foundations

## Task M0.5: Frozen fixtures and doctor command

**Files:** Create data/fixtures/synthetic_v1/source/*.csv, data/fixtures/synthetic_v1/manifest.json, artifacts/golden/synthetic_v1/README.md, scripts/verify_fixture_integrity.py, apps/cli/main.py, quantlab/application/doctor.py, tests/fixtures/test_synthetic_fixture.py, tests/application/test_doctor.py.

**Interfaces:** DoctorService.run() -> DoctorReport with PASS/WARN/FAIL checks; verify_fixture(path) -> FixtureIntegrityReport. Synthetic data must be human-computable and include AAPL plus at least one second instrument, a rename, split, dividend, filing/restatement spanning the 2020-03-01 decision canary, missing fundamental, missing open, delisting uncertainty, and at least 36 monthly decision dates.

- [ ] Add fixed expected counts/hashes and tests test_fixture_contains_required_temporal_canaries, test_fixture_hash_detects_mutation, test_doctor_offline_success, and test_doctor_redacts_secrets.
- [ ] Run python -m pytest tests/fixtures tests/application/test_doctor.py -q; expected failure is missing fixture and command.
- [ ] Add reviewed fixture values and doctor checks for Python, config, PostgreSQL, artifacts, DuckDB, calendar, paths, and optional keys/broker.
- [ ] Run python scripts/verify_fixture_integrity.py data/fixtures/synthetic_v1 and quantlab doctor --offline; expected PASS with optional external services reported WARN, not hidden.
- [ ] Commit: test: add frozen QuantLab synthetic fixture and doctor

## M0 Gate

Run:

~~~bash
python -m pytest tests/domain tests/common tests/architecture tests/infrastructure tests/fixtures tests/application/test_doctor.py tests/test_milestone_gates.py -q
python -m ruff check .
python -m ruff format --check .
python -m mypy quantlab apps
docker compose config --quiet
quantlab doctor --offline
python scripts/verify_milestone.py M0 --require-prior
~~~

Acceptance: offline CI passes; architecture boundaries are enforced; storage and fixture hashes are reproducible; doctor passes. Assert repository absence of apps/web, apps/mcp, quantlab/agents, factor strategies, ML models, and LLM dependencies. Commit checkpoint: chore(gate): accept M0.

# M1 — Point-in-Time Data

## Task M1.1: Instrument master and symbol history

**Files:** Create quantlab/data/instruments.py, quantlab/infrastructure/instrument_repository.py, migrations/versions/0002_instruments.py; tests/data/test_instruments.py, tests/integration/test_instrument_repository.py.

**Interfaces:** InstrumentRepository.resolve(symbol, exchange, as_of) -> InstrumentId | None; history(instrument_id) -> tuple[SymbolHistory, ...]; upsert_identity(source_record) -> Instrument.

- [ ] Test overlapping history rejection, historical symbol resolution, ticker reuse across different instruments, rename invariance, and delisted-but-historical lookup.
- [ ] Run the two test files; expected failure is missing repository behavior.
- [ ] Implement interval constraints and source provenance without using ticker as a primary key.
- [ ] Run the two test files; expected all pass.
- [ ] Commit: feat(data): add point-in-time instrument identity

## Task M1.2: Provider protocols and immutable raw snapshots

**Files:** Create quantlab/data/providers/base.py, market.py, listings.py, fundamentals.py, macro.py, actions.py, adapters/yahoo_daily.py, adapters/sec_edgar.py, adapters/fred_alfred.py, adapters/public_listings.py, quantlab/data/raw.py, quantlab/infrastructure/raw_snapshot_repository.py; tests/data/test_provider_contracts.py, test_provider_recordings.py, test_raw_snapshots.py; data/fixtures/provider-recordings/*.json.

**Interfaces:** Each provider fetch(request) -> ProviderBatch; RawSnapshotService.capture(provider, request) -> RawSnapshotRef. RawSnapshotRef includes provider, request hash, fetched_at, content hash, license/source metadata, and immutable bytes URI.

- [ ] Test provider exceptions become structured failures, repeat capture reuses identical content without overwrite, changed bytes create a new snapshot, and provider types never enter domain entities.
- [ ] Run the named tests; expected failure is missing protocols/snapshot service.
- [ ] Implement protocols, recorded-response contract tests, fake providers for CI, and replaceable free-source adapters; real network calls remain explicitly opt-in and are never called by offline tests.
- [ ] Run the named tests with QUANTLAB_OFFLINE=1; expected all pass.
- [ ] Commit: feat(data): capture immutable provider snapshots

## Task M1.3: Market bars and corporate-action normalization

**Files:** Create quantlab/data/normalize/market.py, actions.py, quantlab/data/quality/market.py; migrations/versions/0003_market_actions.py; tests/data/test_market_normalization.py, test_corporate_actions.py, test_market_quality.py.

**Interfaces:** normalize_bars(snapshot, instrument_map) -> NormalizationBatch[MarketBar]; normalize_actions(...) -> NormalizationBatch[CorporateAction]; MarketQualityEvaluator.evaluate(batch) -> DataQualityReport.

- [ ] Test OHLC inequalities, uniqueness, nonnegative volume, raw/adjusted semantic separation, split/dividend/symbol/delisting mapping, missing terminal-value severity, and no adjusted-price-plus-cash double count marker.
- [ ] Run the named tests; expected failure is missing normalizers.
- [ ] Implement deterministic normalization with rejected-row artifacts and source-record lineage.
- [ ] Run the named tests; expected all pass.
- [ ] Commit: feat(data): normalize market data and corporate actions

## Task M1.4: SEC facts, normalized fundamentals, and PIT restatements

**Files:** Create quantlab/data/sec/raw_facts.py, normalize.py, mappings.py, pit.py; configs/fundamental-mappings-v1.yaml; migrations/versions/0004_fundamentals.py; tests/data/test_sec_facts.py, test_fundamental_mapping.py, test_pit_fundamentals.py.

**Interfaces:** FundamentalRepository.as_of(instrument_id, metric, decision_time, extra_lag_sessions=1) -> FundamentalObservation | None; normalizer retains accession, source concept, period_end, available_at, mapping version, and raw snapshot id.

- [ ] Create tests where an original filing is available February 20, an amendment April 15, and decisions February 19/March 1/May 1 return none/original/amended respectively after configured session lag.
- [ ] Test current shares are never used for historical market cap and invalid denominator is structured missingness.
- [ ] Run python -m pytest tests/data/test_sec_facts.py tests/data/test_fundamental_mapping.py tests/data/test_pit_fundamentals.py -q; expected failure is missing PIT logic.
- [ ] Implement latest-eligible-filing selection and versioned mappings; rerun tests; expected all pass.
- [ ] Commit: feat(data): add restatement-safe PIT fundamentals

## Task M1.5: Historical listings, liquid universe, and ETF separation

**Files:** Create quantlab/universe/listings.py, eligibility.py, liquidity.py, builder.py, etf.py; configs/universes/us-liquid-1000-v1.yaml, etf-tactical-v1.yaml; tests/universe/test_historical_listings.py, test_liquidity_universe.py, test_etf_separation.py.

**Interfaces:** UniverseBuilder.build(universe_id, session, as_of, data) -> UniverseSnapshot; baseline filters common equities, $5 minimum, 252 sessions, trailing 60-session median dollar volume, deterministic rank, top 1,000 where available.

- [ ] Test 2017-06-30 membership uses historical listings, future listings are absent, delisted names remain eligible before delisting, trailing windows stop at snapshot, liquidity ties use InstrumentId, and ETFs cannot enter equity ranks.
- [ ] Run the named tests; expected failure is missing builder.
- [ ] Implement config-driven eligibility and explicit coverage/survivorship flags.
- [ ] Run the named tests; expected all pass.
- [ ] Commit: feat(universe): build historical liquid equity snapshots

## Task M1.6: Macro vintages, PIT facade, dataset publication, and quality confidence

**Files:** Create quantlab/data/macro.py, queries.py, manifests.py, publication.py, quality/report.py, quantlab/application/datasets.py, apps/cli/datasets.py, configs/data-quality-v1.yaml, configs/datasets/synthetic-v001.yaml; migrations/versions/0005_datasets.py; tests/data/test_macro_vintages.py, test_pit_queries.py, test_dataset_publication.py, test_data_confidence.py; tests/e2e/test_dataset_cli.py.

**Interfaces:** PointInTimeData uses the ledger signature; DatasetPublisher.build(spec) -> DatasetBuild then validate(build) -> DataQualityReport then publish(build, report) -> DatasetManifest. Only PUBLISHED manifests are queryable.

- [ ] Test macro revisions are vintage-aware, every query rejects as_of before available_at, BUILDING datasets cannot be read, content hash changes on source/mapping/universe changes, and flags map deterministically to A/B/C/D without hiding underlying metrics.
- [ ] Run the named tests; expected failure is missing facade/publication.
- [ ] Implement the state machine, canonical manifest hash, bias flags, and partition counts.
- [ ] Run the named tests plus tests/e2e/test_dataset_cli.py with the socket guard offline; expected all pass with no provider call.
- [ ] Commit: feat(data): publish immutable PIT research datasets

## M1 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/data tests/universe tests/integration/test_instrument_repository.py tests/e2e/test_dataset_cli.py -q
quantlab dataset build configs/datasets/synthetic-v001.yaml --offline
quantlab dataset inspect DATASET-v001 --verify-hash
python scripts/verify_milestone.py M1 --require-prior
~~~

Acceptance: historical universe query for 2017-06-30 and Apple-known-fundamental query for 2020-03-01 return fixture-defined values with no future filing; restatement/OHLC/symbol/action tests pass; DATASET-v001 is immutable, PUBLISHED, reproducible, and carries confidence/bias flags. Do not proceed if any PIT critical test fails. Commit checkpoint: chore(gate): accept M1.

# M2 — Factor Research

## Task M2.1: Factor contracts, registry, snapshots, and label isolation

**Files:** Create quantlab/factors/contracts.py, registry.py, snapshots.py, context.py; migrations/versions/0006_factors.py; tests/factors/test_registry.py, test_snapshots.py, test_label_isolation.py; tests/architecture/test_factor_dependencies.py.

**Interfaces:** Factor.compute(FactorContext) -> FactorSnapshot; FactorRegistry.register(definition, implementation_hash) -> FactorVersion; factor context exposes PointInTimeData but no labels namespace.

- [ ] Test methodology change creates a version, snapshot hash is order-invariant, composite available_at is max input availability, and AST/runtime guards reject imports/access to quantlab.ml.labels or future-return columns.
- [ ] Run named tests; expected failure is missing factor boundary.
- [ ] Implement registry/snapshot contracts and architectural isolation.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(factors): define versioned leakage-safe factor contracts

## Task M2.2: Cross-sectional transforms and missingness

**Files:** Create quantlab/factors/transforms.py, missingness.py, neutralization.py; tests/factors/test_transforms.py, test_missingness.py, test_neutralization.py.

**Interfaces:** transform_cross_section(values, TransformSpec) -> TransformedCrossSection; MissingReason enum includes insufficient history, missing fundamental, invalid denominator, stale data, and out of range.

- [ ] Test 1/99 winsorization, percentile ranks with deterministic average ties, z/robust-z, direction reversal, no universal zero fill, within-sector rank, UNKNOWN sector, and regression neutralization on a hand-computable fixture.
- [ ] Run named tests; expected failure is missing transforms.
- [ ] Implement stateless deterministic transforms with explicit null/status propagation.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(factors): add deterministic cross-sectional transforms

## Task M2.3: V1 factor definitions

**Files:** Create quantlab/factors/momentum.py, value.py, quality.py, growth.py, risk.py; tests/factors/test_momentum.py, test_value.py, test_quality.py, test_growth.py, test_risk.py; docs/calculators/factors-v1.md.

**Interfaces:** Register momentum_12_1, momentum_6_1, earnings_yield, book_to_market, fcf_yield, roe, roa, gross_profitability, accrual_quality, revenue_growth, operating_income_growth, volatility_60d, max_drawdown_252d, and beta. Each definition specifies formula, direction, inputs, lookback, availability, missingness, price semantic, and calculator version.

- [ ] Add hand-computed synthetic formula tests, insufficient-history boundaries, zero/negative denominator cases, split/dividend consistency, and a future-filing canary for every fundamental family.
- [ ] Run the five test files; expected failure is missing factors.
- [ ] Implement only the listed factor set using total-return-aware research inputs and PIT fundamentals.
- [ ] Run the five test files; expected all pass and documented values match fixture arithmetic.
- [ ] Commit: feat(factors): implement reviewed V1 factor set

## Task M2.4: Factor evaluation and deterministic composites

**Files:** Create quantlab/factors/evaluation.py, composites.py, quantiles.py; configs/factors/composite-v1.yaml; tests/factors/test_evaluation.py, test_composites.py, test_factor_golden.py.

**Interfaces:** FactorEvaluator.evaluate(snapshot, ForwardReturnView, EvaluationSpec) -> FactorResearchResult; CompositeBuilder.build(snapshots, CompositeSpec) -> AlphaSnapshot. Baseline weights are Momentum 30%, Quality 25%, Value 20%, Growth 15%, Low Volatility 10%; equal-factor and momentum-only are separate ids.

- [ ] Test Pearson/Spearman IC, IC IR, positive frequency, 1/3/6/12M decay, quantile returns/Q5-Q1 diagnostic, coverage, turnover, correlation, subperiod/sector/size diagnostics, and exact golden rankings.
- [ ] Run named tests; expected failure is missing evaluation/composite behavior.
- [ ] Implement calculator-versioned results and deterministic tie/order handling; diagnostic long-short spread must be labeled non-deployable.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(factors): add research analytics and baseline composite

## Task M2.5: Factor research application command and artifact lineage

**Files:** Create quantlab/application/factor_research.py, apps/cli/factors.py; tests/application/test_factor_research.py, tests/e2e/test_factor_cli.py; docs/contracts/factor-research-result.md.

**Interfaces:** FactorResearchService.run(dataset_id, factor_id, spec) -> FactorResearchResultRef; command quantlab factor research FACTOR --dataset DATASET --output json.

- [ ] Test published-dataset requirement, identical rerun hash, dataset/factor/code/config lineage, offline execution, structured warnings, and immutable result artifact.
- [ ] Run named tests; expected failure is missing service/CLI.
- [ ] Implement orchestration only; CLI must not calculate metrics itself.
- [ ] Run named tests and run command twice; expected identical artifact hash.
- [ ] Commit: feat(cli): expose reproducible factor research workflow

## M2 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/factors tests/application/test_factor_research.py tests/e2e/test_factor_cli.py tests/architecture/test_factor_dependencies.py -q
quantlab factor research momentum_12_1 --dataset DATASET-v001 --output json
quantlab factor composite composite-v1 --dataset DATASET-v001 --output json
python scripts/verify_milestone.py M2 --require-prior
~~~

Acceptance: factor research is reproducible from dataset id; all 14 listed factors, analytics, golden rankings, and deterministic composite pass; no ML package/model is used. Commit checkpoint: chore(gate): accept M2.

# M3 — Portfolio + Authoritative Event-Driven Backtest

## Task M3.1: Top-K selection, buffer, and weighting

**Files:** Create quantlab/portfolio/selection.py, weighting.py, construction.py; configs/strategies/composite-top30-v1.yaml; tests/portfolio/test_selection.py, test_weighting.py, test_construction_properties.py.

**Interfaces:** PortfolioConstructor.construct(ConstructionRequest) -> TargetPortfolio. ConstructionRequest includes AlphaSnapshot, UniverseSnapshot, current PortfolioSnapshot, PortfolioSpec, MarketSnapshot, and decision_time.

- [ ] Test Top-30 entry/Top-40 hold, deterministic exit/entry priority, equal weights, inverse-vol research variant, no fractional quantities after order planning, residual cash, input-row-order invariance, and no use of future ranks.
- [ ] Run named tests; expected failure is missing constructor.
- [ ] Implement selection before weighting and preserve reasons TOP_K_ENTRY, BUFFER_HOLD, and FORCED_EXIT.
- [ ] Run named tests including 500 Hypothesis examples; expected all pass.
- [ ] Commit: feat(portfolio): construct deterministic Top-K portfolios

## Task M3.2: Constraints, risk engine, and order planner

**Files:** Create quantlab/portfolio/constraints.py, risk.py, liquidity.py, diagnostics.py, orders.py; configs/risk/equity-v1.yaml; tests/portfolio/test_constraints.py, test_risk_properties.py, test_order_planner.py, test_capacity.py.

**Interfaces:** RiskEngine.apply(target, current, market, RiskSpec) -> RiskDecision; OrderPlanner.plan(current, approved_target, prices, cash) -> OrderPlan. Rules return PASS/ADJUST/REJECT plus reason and before/after values.

- [ ] Test 5% name cap, 30% sector cap, unknown-sector cap, gross/cash, ADV participation, minimum trade, no-trade band, optional turnover budget, impossible-constraint rejection, and maximum-iteration termination.
- [ ] Test long-only/nonnegative weights, weight/cash conservation, deterministic integer sizing, and symbol/split invariance with property tests.
- [ ] Run named tests; expected failure is missing risk/order behavior.
- [ ] Implement ordered, versioned rules and structured adjustment reasons; rerun tests; expected all pass.
- [ ] Commit: feat(portfolio): enforce risk and produce auditable orders

## Task M3.3: Clock, calendar, events, and order state machine

**Files:** Create quantlab/backtest/clock.py, calendar.py, events.py, ordering.py, order_state.py; configs/backtest/event-order-v1.yaml; tests/backtest/test_clock.py, test_calendar.py, test_event_ordering.py, test_order_state.py.

**Interfaces:** HistoricalClock.events(start, end) -> Iterator[SessionEvent]; EventSequencer.order(events) -> tuple[Event, ...]; transition(order, event) -> Order. America/New_York market semantics convert to UTC internally.

- [ ] Test holidays/weekends/DST, session close decision then next eligible open, exact versioned event priority, allowed/forbidden order transitions, and absence of wall-clock calls in quant modules.
- [ ] Run named tests; expected failure is missing engine primitives.
- [ ] Implement calendar-driven immutable events and exhaustive transition table.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(backtest): add deterministic simulation time and events

## Task M3.4: Simulated broker, execution, slippage, costs, and partial fills

**Files:** Create quantlab/backtest/broker.py, execution.py, costs.py, participation.py; tests/backtest/test_execution.py, test_costs.py, test_partial_fills.py, test_missing_open.py.

**Interfaces:** SimulatedBroker.submit(Order, MarketSnapshot) returns updated Order and fills; NextOpenExecution.reference_price(order, market) -> Decimal; CostBreakdown separates commission, slippage, and modeled impact.

- [ ] Test buys/sells receive adverse fixed-bps slippage, same-close orders cannot fill, weekend gap uses Monday open, missing open yields pending/reject policy with warning rather than previous close, and participation cap creates exact partial fill/remaining quantity.
- [ ] Run named tests; expected failure is missing broker.
- [ ] Implement market orders only, zero-commission configurable baseline, modeled costs labeled modeled, and deterministic rounding.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(backtest): simulate executable next-open fills and costs

## Task M3.5: Ledgers, corporate actions, and accounting conservation

**Files:** Create quantlab/backtest/ledger.py, accounting.py, corporate_actions.py, marking.py; tests/backtest/test_accounting.py, test_split.py, test_dividend.py, test_symbol_change.py, test_delisting.py, test_accounting_properties.py.

**Interfaces:** AccountingEngine.apply(state, event) -> AccountingState; mark_to_market(state, market, session) -> PortfolioSnapshot. Separate cash, positions, transactions, corporate actions, realized/unrealized PnL, dividends, and costs.

- [ ] Test buy/sell round trip, split value conservation, ex/pay-date dividend policy, no dividend double count, rename invariance, observed delisting terminal value, missing terminal severe warning, stale mark, and pre-tax weighted-average cost.
- [ ] Run named tests; expected failure is missing accounting.
- [ ] Implement append-only ledgers and Decimal-based conservation; never patch positions directly.
- [ ] Run named tests including randomized conservation sequences; expected all pass.
- [ ] Commit: feat(backtest): add auditable portfolio accounting ledgers

## Task M3.6: Simulation engine, analytics, golden replay, and CLI

**Files:** Create quantlab/backtest/engine.py, result.py, quantlab/analytics/performance.py, benchmark.py, attribution.py, quantlab/application/backtests.py, apps/cli/backtests.py, scripts/compare_golden.py; tests/backtest/test_engine.py, test_golden_backtest.py, test_deterministic_replay.py, tests/analytics/test_performance.py, tests/e2e/test_backtest_cli.py; docs/calculators/performance-v1.md.

**Interfaces:** BacktestEngine.run(BacktestSpec) -> BacktestResult; PerformanceCalculator.calculate(returns, benchmark, spec) -> PerformanceMetrics; quantlab backtest run CONFIG --dataset DATASET --offline.

- [ ] Add human-derived expected event/order/fill/cash/position/equity rows for the synthetic golden backtest and a frozen real-market regression slice.
- [ ] Test total return, CAGR, volatility, Sharpe/risk-free assumption, Sortino, drawdown/duration/recovery, Calmar, beta/alpha, tracking error, turnover, costs, SPY excess return, validity status, and two-run byte-identical authoritative artifacts.
- [ ] Run named tests; expected failure is missing engine/calculators.
- [ ] Implement event loop and versioned calculators; fast/vectorized results must never populate BacktestResult authority fields.
- [ ] Run named tests plus CLI twice offline; expected all pass with identical hashes.
- [ ] Commit: feat(backtest): deliver authoritative event-driven simulation

## M3 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/portfolio tests/backtest tests/analytics tests/e2e/test_backtest_cli.py -q
quantlab backtest run configs/strategies/composite-top30-v1.yaml --dataset DATASET-v001 --offline
python scripts/compare_golden.py artifacts/latest/backtest artifacts/golden/synthetic_v1/backtest
python scripts/verify_milestone.py M3 --require-prior
~~~

Acceptance: baseline multi-year simulation emits orders, fills, cash, positions, equity, costs, audit trail, SPY-relative metrics, and VALID/VALID_WITH_WARNINGS/INVALID status; next-open, gap, missing-open, actions, conservation, event order, and deterministic replay pass. QuantLab is usable without ML/agent/UI. Commit checkpoint: chore(gate): accept M3.

# M4 — Validation and Falsification

## Task M4.1: Partitions, candidate freeze, holdout ledger, and hard correctness gates

**Files:** Create quantlab/validation/partitions.py, candidate.py, holdout.py, gates.py; migrations/versions/0007_validation.py; configs/validation/default-v1.yaml; tests/validation/test_partitions.py, test_candidate_freeze.py, test_holdout_ledger.py, test_hard_gates.py.

**Interfaces:** CandidateFreezer.freeze(ExperimentSpec, code_fingerprint) -> FrozenCandidate; HoldoutService.open(candidate_id, partition_id, actor, purpose) -> HoldoutAccess; HardGateEvaluator.evaluate(evidence) -> tuple[GateDecision, ...].

- [ ] Test disjoint time partitions, label-horizon boundary checks, immutable strategy hash, access audit, consumed holdout permanence, revised-candidate new id, and nonoverrideable leakage/data/authority/reproducibility/trial-ledger failures.
- [ ] Run named tests; expected failure is missing lockbox services.
- [ ] Implement transactional one-way holdout consumption and universal hard gates.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(validation): enforce candidate freeze and lockbox discipline

## Task M4.2: Robustness matrix and ablations

**Files:** Create quantlab/validation/robustness.py, sensitivity.py, ablation.py, concentration.py, execution_stress.py; tests/validation/test_sensitivity.py, test_ablation.py, test_concentration.py, test_execution_stress.py.

**Interfaces:** RobustnessRunner.run(candidate, ValidationSpec) -> RobustnessArtifact containing parameter surfaces, Top-K 20/30/50, equal/inverse-vol, universe/subperiod/sector, 0/5/10/20/50 bps costs, execution timing, filing lag, and factor/feature-group ablations.

- [ ] Test every configured cell is retained, plateau/spike classification on synthetic surfaces, best-year/stock/sector concentration, break-even cost, delay fragility, leave-one-sector-out, and no cherry-picked cell removal.
- [ ] Run named tests; expected failure is missing runner.
- [ ] Implement deterministic scenario ids and reuse frozen base inputs/scores where the comparison requires them.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(validation): add systematic robustness and ablation suites

## Task M4.3: Dependence-aware bootstrap and statistical diagnostics

**Files:** Create quantlab/validation/bootstrap.py, multiple_testing.py, deflated_sharpe.py, fdr.py, negative_controls.py; tests/validation/test_bootstrap.py, test_multiple_testing.py, test_deflated_sharpe.py, test_fdr.py, test_negative_controls.py; docs/calculators/statistics-v1.md.

**Interfaces:** BootstrapRunner.run(returns, BootstrapSpec, seed) -> BootstrapDistribution; TrialDiagnostics.evaluate(trials) -> MultipleTestingEvidence. Store method, block rule/length, simulations, seed, quantiles, and warnings.

- [ ] Test stationary/block resampling preserves length/order blocks, reproducible quantiles, pure-noise intervals, raw trial retention, reviewed Deflated Sharpe formula examples, Benjamini-Hochberg results, label-shuffle collapse, and random-noise control.
- [ ] Run named tests; expected failure is missing statistics.
- [ ] Implement methods with calculator versions and language stating uncertainty estimate, not future guarantee; exclude PBO/CSCV from this gate.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(validation): quantify uncertainty and multiple testing

## Task M4.4: Trial ledger, deterministic verdicts, and validation artifacts

**Files:** Create quantlab/validation/trials.py, verdicts.py, result.py, runner.py, quantlab/application/validation.py, apps/cli/validation.py; migrations/versions/0008_trials.py; tests/validation/test_trial_ledger.py, test_verdicts.py, test_validation_runner.py.

**Interfaces:** TrialLedger.record_once(campaign_id, trial_spec) -> TrialRecord; ValidationRunner.run(...) -> ValidationResult with REJECTED, RESEARCH_ONLY, VALIDATED, or PAPER_CANDIDATE. PAPER_VALIDATED is reserved for M6 evidence.

- [ ] Test failed/rejected trials cannot be deleted, duplicate specs reference existing trials, hard failure always REJECTED, soft thresholds are config-specific, all evidence hashes are retained, and reruns are deterministic.
- [ ] Run named tests; expected failure is missing runner/verdicts.
- [ ] Implement an append-only ledger and deterministic rules; LLM critic fields are absent from verdict computation.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(validation): produce deterministic validation verdicts

## Task M4.5: Red-team demonstrations

**Files:** Create configs/red-team/lookahead.yaml, random-mining.yaml, cost-illusion.yaml, apps/cli/red_team.py; tests/red_team/test_lookahead_rejected.py, test_random_mining_warned.py, test_cost_illusion_rejected.py; docs/research/red-team-v1.md.

**Interfaces:** RedTeamRunner.run(case_id, dataset_id) -> ValidationResultRef. The look-ahead case must use a deliberate future-return canary; random mining records every trial; cost illusion uses the authoritative cost engine.

- [ ] First run each case against its intended detector disabled in an isolated test double and confirm the synthetic fake result looks attractive.
- [ ] Run python -m pytest -q tests/red_team/test_lookahead_rejected.py tests/red_team/test_random_mining_warned.py tests/red_team/test_cost_illusion_rejected.py; expected failure is missing red-team configurations and runner.
- [ ] Enable real hard gates/diagnostics and assert look-ahead is REJECTED/INVALID, random mining emits multiple-testing warning with exact trial count, and high-turnover edge disappears at configured realistic cost.
- [ ] Run python -m pytest tests/red_team -q; expected all pass deterministically.
- [ ] Commit: test(validation): add flagship falsification demonstrations

## M4 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/validation tests/red_team -q
quantlab validate run configs/validation/default-v1.yaml --experiment EXP-SYNTHETIC --offline
quantlab red-team run --all --dataset DATASET-v001 --offline
python scripts/verify_milestone.py M4 --require-prior
~~~

Acceptance: lockbox, trial retention, robustness, bootstrap, and deterministic verdicts pass; the three red-team cases produce their exact expected outcomes. No ML implementation, agent, MCP, or dashboard exists. Commit checkpoint: chore(gate): accept M4.

# M5 — ML Ranking

## Task M5.1: Executable labels, monthly panel, and leakage boundary

**Files:** Create quantlab/ml/labels.py, panel.py, leakage.py, schemas.py; tests/ml/test_labels.py, test_panel.py, test_leakage_guard.py; tests/architecture/test_ml_boundaries.py.

**Interfaces:** LabelBuilder.build(dataset_id, rebalance_dates, LabelSpec) -> LabelSnapshot; PanelBuilder.build(features, labels, PanelSpec) -> MonthlyPanel. Labels use next-session-open entry and next-rebalance exit/measurement with actions; inference panel has no label columns.

- [ ] Test gap-aware entry, corporate-action-aware return, benchmark-relative/rank labels, future feature canary rejection, factor→label import prohibition, PIT feature availability, and instrument-date uniqueness.
- [ ] Run named tests; expected failure is missing ML data boundary.
- [ ] Implement labels in a distinct namespace and schema-level feature allowlist.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(ml): build executable leakage-safe ranking panels

## Task M5.2: Purged walk-forward splits and train-only preprocessing

**Files:** Create quantlab/ml/splits.py, preprocessing.py; configs/ml/walk-forward-v1.yaml; tests/ml/test_walk_forward.py, test_purge_embargo.py, test_preprocessing.py, test_ranking_groups.py.

**Interfaces:** WalkForwardSplitter.split(panel, SplitSpec) -> tuple[WalkForwardFold, ...]; fit_transform_train(fold, PreprocessSpec) -> FittedPreprocessor; ranking group key is rebalance_date.

- [ ] Test chronological five-year-style training windows, quarterly retrain/monthly inference, label-overlap purge, one-rebalance embargo, no fitted parameter from validation/test, and no cross-date ranking group.
- [ ] Run named tests; expected failure is missing split/preprocess logic.
- [ ] Implement expanding/rolling modes and serialize fold membership hashes.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(ml): enforce purged walk-forward evaluation

## Task M5.3: Ridge baseline and LightGBM ranking challenger

**Files:** Create quantlab/ml/models/base.py, ridge.py, lightgbm_ranker.py, seeds.py; configs/ml/ridge-v1.yaml, lightgbm-ranker-v1.yaml; tests/ml/test_ridge.py, test_lightgbm_ranker.py, test_model_reproducibility.py, test_synthetic_signal.py, test_label_shuffle.py.

**Interfaces:** RankingModel follows the ledger signature. Training accepts only TrainingPanel and fixed budgeted parameters; prediction requires explicit PredictionSplit.

- [ ] Test synthetic linear signal is learned by Ridge, grouped nonlinear signal by LightGBM, label shuffle collapses OOS Rank IC to configured tolerance, seeds/thread counts are recorded, and identical runs hash equally on supported platform.
- [ ] Run named tests; expected failure is missing models.
- [ ] Implement Ridge and LightGBM only; no XGBoost/deep/RL models and no tuning by final backtest Sharpe.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(ml): add Ridge and LightGBM ranking models

## Task M5.4: Model registry, immutable prediction snapshots, and OOS enforcement

**Files:** Create quantlab/ml/registry.py, predictions.py, training.py; migrations/versions/0009_models_predictions.py; tests/ml/test_model_registry.py, test_predictions.py, test_oos_enforcement.py.

**Interfaces:** ModelRegistry.register(ModelArtifact) -> ModelVersion; PredictionRepository.publish(snapshot) -> PredictionRef. Split enum is TRAIN/VALIDATION/TEST/PAPER_SHADOW/PAPER_ACTIVE.

- [ ] Test registry lineage/hash, prediction immutability, score/rank/percentile consistency, TRAIN rejection by PortfolioBacktestInput, allowed VALIDATION/TEST, and corrupted model artifact rejection.
- [ ] Run named tests; expected failure is missing registry/enforcement.
- [ ] Implement hashed model artifacts and an explicit authoritative-input validator.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(ml): register models and enforce OOS predictions

## Task M5.5: OOS model comparison and champion/challenger decision

**Files:** Create quantlab/ml/evaluation.py, comparison.py, quantlab/application/model_research.py, apps/cli/models.py; tests/ml/test_evaluation.py, test_comparison.py, tests/e2e/test_model_comparison_cli.py; docs/contracts/model-comparison.md.

**Interfaces:** ModelComparisonService.compare(dataset_id, fold_spec, model_specs, portfolio_spec) -> ModelComparisonResult containing simple composite, equal-factor, momentum-only, Ridge, and LightGBM OOS evidence.

- [ ] Test Rank IC/stability, quantiles, importance/permutation importance, fold stability, turnover, OOS portfolio metrics, complexity/benefit labels, and rule that ML losing leaves simple composite champion without failing the milestone.
- [ ] Run named tests; expected failure is missing comparison.
- [ ] Implement evaluation through existing M3/M4 services; no duplicate metric/backtest logic.
- [ ] Run named tests and CLI; expected pass whether challenger wins or loses fixture evidence.
- [ ] Commit: feat(ml): compare challengers against simple baselines

## M5 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/ml tests/architecture/test_ml_boundaries.py tests/e2e/test_model_comparison_cli.py -q
quantlab model compare --dataset DATASET-v001 --walk-forward configs/ml/walk-forward-v1.yaml --models composite,ridge,lightgbm --offline
python scripts/verify_milestone.py M5 --require-prior
~~~

Acceptance: composite/Ridge/LightGBM comparison uses only purged OOS predictions; TRAIN input is rejected; future canary and label-shuffle tests pass; simple composite remains champion if ML lacks robust incremental value. Commit checkpoint: chore(gate): accept M5.

# M6 — Paper Trading and Forward Evidence

## Task M6.1: Versioned paper deployments, persistent runs, and real clock scheduling

**Files:** Create quantlab/paper/deployments.py, runs.py, scheduler.py, clock.py; migrations/versions/0010_paper_deployments_runs.py; tests/paper/test_deployment_freeze.py, test_scheduler_idempotency.py, test_paper_run_state.py, test_real_clock.py, test_paper_job_priority.py.

**Interfaces:** PaperDeploymentService.create(FrozenCandidate, mode) -> PaperDeployment; PaperScheduler.ensure_run(deployment_id, session) -> PaperRun. Idempotency key is deployment_id + expected session + run type.

- [ ] Test deployment changes create versions, duplicate delivery returns same run/order intent, DST/session schedule, paper-critical jobs outrank batch research under constrained workers, and recovery from each persistent state boundary.
- [ ] Run named tests; expected failure is missing paper lifecycle.
- [ ] Implement explicit state machine and persistent idempotency uniqueness.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(paper): add frozen deployments and idempotent runs

## Task M6.2: Latest-data gates and immutable forward predictions

**Files:** Create quantlab/paper/data_gate.py, inference.py, predictions.py; migrations/versions/0011_paper_predictions.py; tests/paper/test_data_gate.py, test_prediction_immutability.py, test_paper_inference.py.

**Interfaces:** PaperInferenceService.run(PaperRun) -> PaperPredictionSnapshot; DataGate.evaluate(session, snapshot) -> GateDecision. Snapshot split is PAPER_ACTIVE or PAPER_SHADOW and is persisted before market outcome.

- [ ] Test stale session, coverage gap, unpublished snapshot, missing/corrupt model, risk-engine failure, immutable prediction, and invalidation-without-overwrite.
- [ ] Run named tests; expected failure is missing services.
- [ ] Reuse M1/M2/M5 inference and M3 portfolio/risk code; no paper-only quant formulas.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(paper): gate data and freeze forward predictions

## Task M6.3: Internal paper broker, execution, accounting, and reconciliation

**Files:** Create quantlab/paper/broker.py, execution.py, accounting.py, reconciliation.py, incidents.py; migrations/versions/0012_paper_orders_fills_incidents.py; tests/paper/test_internal_broker.py, test_reconciliation.py, test_uncertain_submission.py, test_incidents.py.

**Interfaces:** InternalPaperBroker implements PaperBroker and reuses M3 execution/accounting. ReconciliationResult compares expected vs broker cash, positions, orders, and fills; corrections are append-only adjustments.

- [ ] Test next-open execution, duplicate submit_once, uncertain response reconciled before retry, cash/position mismatch incident, freeze-new-orders policy, and no silent database correction.
- [ ] Run named tests; expected failure is missing broker/reconciliation.
- [ ] Implement the internal deterministic broker only; external adapters remain outside the gate.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(paper): execute and reconcile internal paper trades

## Task M6.4: Champion/challenger, drift, divergence, kill switch, and evidence maturity

**Files:** Create quantlab/paper/champion.py, drift.py, divergence.py, kill_switch.py, evidence.py; configs/paper/default-v1.yaml; tests/paper/test_champion_challenger.py, test_drift.py, test_divergence.py, test_kill_switch.py, test_evidence_maturity.py.

**Interfaces:** ChampionService allows one active champion; challengers create shadow predictions/portfolios only. KillSwitch states ACTIVE/PAUSED/HALTED; evidence uses duration, predictions, rebalances, and independent decision periods.

- [ ] Test shadow cannot submit, no automatic promotion, data-vs-model drift distinction, backtest/paper turnover/cost divergence, operational automatic halt, performance drawdown no default halt, halt blocks new orders but does not liquidate, and evidence never uses “proven.”
- [ ] Run named tests; expected failure is missing controls.
- [ ] Implement deterministic thresholds and auditable operator proposals.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(paper): govern forward evidence and operational safety

## Task M6.5: Full simulated month-end forward flow and crash matrix

**Files:** Create quantlab/paper/service.py, quantlab/application/paper.py, apps/cli/paper.py; tests/e2e/test_paper_forward_flow.py, tests/faults/test_paper_crash_matrix.py, test_duplicate_delivery.py, test_secret_redaction.py; docs/runbooks/paper-recovery.md.

**Interfaces:** PaperService.process_session(deployment_id, session) -> PaperRunResult; CLI quantlab paper simulate --deployment ID --sessions RANGE --clock fixture.

- [ ] Parameterize crash injection after data gate, snapshot publish, prediction persist, order plan, broker submit, fill persist, accounting, and reconciliation; restart must converge without duplicate orders/fills.
- [ ] Test month-end→next-open→outcome linkage and forward Rank IC, non-rebalance marking/actions/reconciliation, secret redaction, and PAPER_CANDIDATE→PAPER_VALIDATED only after configured maturity/gates.
- [ ] Run named tests; expected failure is missing end-to-end service.
- [ ] Implement resumable orchestration over existing components; rerun twice from every crash point; expected one canonical result.
- [ ] Commit: feat(paper): complete recoverable forward-test workflow

## M6 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/paper tests/faults tests/e2e/test_paper_forward_flow.py -q
quantlab paper simulate --deployment PAPER-SYNTHETIC --sessions 2024-01-01:2024-04-30 --clock fixture --offline
python scripts/verify_milestone.py M6 --require-prior
~~~

Acceptance: simulated real-clock month-end flow, immutable predictions, internal orders/fills/accounting, reconciliation, champion/shadow isolation, drift/divergence, incidents, kill switch, idempotency, and crash recovery pass. No LLM/MCP/web code exists. Commit checkpoint: chore(gate): accept M6.

# M7 — Agentic Research + MCP

## Task M7.1: Campaigns, hypotheses, and typed ExperimentSpec

**Files:** Create quantlab/research/campaigns.py, hypotheses.py, experiment_spec.py, factor_spec.py, schemas.py; migrations/versions/0013_research_campaigns.py; tests/research/test_campaigns.py, test_hypotheses.py, test_experiment_spec.py, test_factor_spec.py.

**Interfaces:** Hypothesis contains claim, mechanism, expected evidence, and falsification condition. ExperimentSpec contains dataset, universe, factors/model, portfolio, execution, validation, and budget; validate_experiment_spec(spec) -> ValidatedExperimentSpec.

- [ ] Test missing falsification rejection, unsupported scope rejection, budget presence, frozen config hash/new experiment id after observed-result change, valid “no edge” conclusion, safe add/subtract/multiply/divide/rolling mean/std/return/rank/z-score/log/backward-lag factor expressions, and rejection of LEAD/eval/import/shell/file/network operators.
- [ ] Run named tests; expected failure is missing research contracts.
- [ ] Implement strict Pydantic boundary schemas mapped into dependency-free domain/application values.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(research): define falsifiable campaigns and experiments

## Task M7.2: Budgets, permission gateway, and typed tool registry

**Files:** Create quantlab/agents/permissions.py, budgets.py, tools/registry.py, tools/schemas.py, tools/services.py; configs/agents/roles-v1.yaml, budgets-v1.yaml; tests/agents/test_permissions.py, test_budgets.py, test_tool_registry.py, test_prompt_injection.py.

**Interfaces:** PermissionGateway.authorize(actor, ToolCall, CampaignState) -> AuthorizationDecision; ToolExecutor.execute(AuthorizedToolCall) -> StructuredToolResult. Standard tools cover dataset/factor/model inspection, experiment creation, factor research, train/evaluate, backtest, compare, robustness/ablation/cost stress, paper status, and report generation.

- [ ] Test schema validation before role/budget, denial of shell/Python/SQL/database mutation/result mutation/direct paper order/secrets, immutable budgets, concurrency/step/token/cost limits, and prompt text unable to elevate permission.
- [ ] Run named tests; expected failure is missing gateway.
- [ ] Implement a default-deny allowlist that invokes existing application services rather than quant logic in tools.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(agents): enforce typed tools and research budgets

## Task M7.3: LLM provider adapter, run registry, and three constrained roles

**Files:** Create quantlab/agents/providers/base.py, fake.py, runs.py, research_agent.py, orchestrator.py, critic.py; migrations/versions/0014_agent_runs.py; tests/agents/test_fake_provider.py, test_run_registry.py, test_roles.py, test_agent_resume.py, test_step_limits.py.

**Interfaces:** LLMProvider.generate(AgentRequest) -> AgentResponse; deterministic FakeLLMProvider is the only provider used in normal CI. AgentRun records role/prompt/tool-schema/provider/model/settings/input/output hashes/tokens/latency/cost/campaign and resumable state.

- [ ] Test deterministic fake responses, role separation, crash/resume, max steps, cost/token accounting, malformed output rejection, and no quant metric calculation path inside agents.
- [ ] Run named tests; expected failure is missing adapters/roles.
- [ ] Implement Research Agent, Experiment Orchestrator, and Quant Critic as state machines over authorized typed tools; no swarm/delegated order authority.
- [ ] Run named tests; expected all pass without internet or real model.
- [ ] Commit: feat(agents): add resumable constrained research roles

## Task M7.4: Claim grounding, failed-trial visibility, and research reports

**Files:** Create quantlab/research/claims.py, reports.py, memory.py, duplicate_detection.py, quantlab/agents/claim_verifier.py, apps/cli/reports.py; tests/research/test_claims.py, test_reports.py, test_duplicate_detection.py, tests/agents/test_claim_verifier.py, test_result_tampering.py.

**Interfaces:** QuantClaim(value, unit, artifact_id, metric_path, calculator_version); ClaimVerifier.verify(report, ArtifactResolver) -> ClaimVerificationResult; ReportBuilder.build(campaign_id) -> ResearchReportRef.

- [ ] Test every number must resolve exactly to immutable artifact data, unsupported/altered numbers fail, FACT vs INTERPRETATION is explicit, rejected/failed variants and raw trial count appear, duplicate identical experiments reference existing result, and semantic index absence cannot change authority.
- [ ] Run named tests; expected failure is missing verifier/report builder.
- [ ] Implement structured PostgreSQL/artifact memory as authority; semantic retrieval remains excluded from the M7 gate.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(research): ground quantitative claims in artifacts

## Task M7.5: MCP adapter and end-to-end quality-plus-momentum campaign

**Files:** Create apps/mcp/server.py, tools.py, schemas.py, apps/cli/campaigns.py; quantlab/application/research_campaigns.py; tests/mcp/test_mcp_tools.py, test_mcp_permissions.py, tests/e2e/test_agent_campaign.py; configs/campaigns/quality-improves-momentum-v1.yaml.

**Interfaces:** MCP is a transport adapter over ToolExecutor/application services; it exposes no raw database, shell, Python, secret, or broker-order primitive. Campaign command returns hypothesis→experiments→comparison→ablation→validation→critic→grounded report lineage.

- [ ] Test MCP schema parity, authorization, timeouts/structured errors, prompt-injection non-escalation, lockbox restrictions, budget exhaustion, failed experiment retention, direct-order denial, and claim verification.
- [ ] Run named tests with FakeLLMProvider; expected failure is missing adapter/campaign service.
- [ ] Implement adapter and approved flagship question workflow; agents may conclude quality adds no robust value.
- [ ] Run named tests twice offline; expected identical deterministic tool/artifact graph apart from recorded run timestamps/ids defined as non-authoritative metadata.
- [ ] Commit: feat(mcp): expose grounded QuantLab research tools

## M7 Gate

Run:

~~~bash
QUANTLAB_OFFLINE=1 python -m pytest tests/research tests/agents tests/mcp tests/e2e/test_agent_campaign.py -q
quantlab campaign run configs/campaigns/quality-improves-momentum-v1.yaml --llm fake --offline
quantlab report verify artifacts/latest/research-report.json
python scripts/verify_milestone.py M7 --require-prior
~~~

Acceptance: the approved question completes through grounded report; unauthorized tools, budgets, malformed specs, tampering, lockbox access, prompt injection, failed-trial deletion, and direct paper orders are denied. Metrics/verdicts remain deterministic artifacts. No dashboard exists. Commit checkpoint: chore(gate): accept M7.

# M8 — API, CLI, and Research Dashboard

## Task M8.1: FastAPI application boundary and asynchronous jobs

**Files:** Create apps/api/main.py, dependencies.py, auth.py, errors.py, routes/datasets.py, factors.py, experiments.py, backtests.py, validation.py, models.py, paper.py, campaigns.py, jobs.py, health.py; apps/worker/main.py, apps/scheduler/main.py; quantlab/infrastructure/telemetry.py; tests/api/test_auth.py, test_routes.py, test_jobs.py, test_health.py, test_telemetry.py; tests/application/test_worker_scheduler.py.

**Interfaces:** HTTP endpoints return ids or persisted job ids for heavy operations; route handlers call application services only. Roles are public-demo/researcher/operator/admin; frontend never queries storage directly.

- [ ] Test request/schema validation, role enforcement in services, long jobs return 202 + job id, idempotency keys, polling states/progress, worker/scheduler restart recovery, paper queue priority, structured latency/failure/queue/data/paper/agent metrics, correlation tracing, safe errors, liveness/readiness/paper readiness, rate limit for demo, and no secret/internal path leakage.
- [ ] Run named tests; expected failure is missing API.
- [ ] Implement API composition and persisted worker dispatch; no metrics are recalculated in route/schema code.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(api): expose secure asynchronous application services

## Task M8.2: First-class CLI parity

**Files:** Modify apps/cli/main.py, datasets.py, factors.py, backtests.py, validation.py, models.py, paper.py, campaigns.py, reports.py; create apps/cli/experiments.py, jobs.py, system.py; tests/cli/test_help.py, test_output.py, test_permissions.py, test_api_parity.py.

**Interfaces:** CLI supports dataset/factor/backtest/validate/model/paper/campaign/job/system workflows with human and --output json formats. Exit codes: 0 success, 2 validation/input, 3 gate/authority, 4 infrastructure/runtime.

- [ ] Test complete help tree, JSON schema parity with API, stable exit codes, offline flags, no hidden raw SQL/shell, and operator-only paper controls.
- [ ] Run named tests; expected failure is missing commands.
- [ ] Compose existing services and schemas; do not fork business logic.
- [ ] Run named tests; expected all pass.
- [ ] Commit: feat(cli): complete QuantLab application interface

## Task M8.3: Next.js shell, typed client, accessibility, and visual foundation

**Files:** Create apps/web/package.json, package-lock.json, next.config.ts, tsconfig.json, app/layout.tsx, app/page.tsx, app/globals.css, lib/api/client.ts, lib/api/types.ts, components/navigation.tsx, components/job-progress.tsx, scripts/check_openapi_web_types.py, tests/web/navigation.spec.ts, accessibility.spec.ts.

**Interfaces:** API types are generated/checked from the FastAPI OpenAPI schema. Shell navigation exactly matches Overview; Research/Campaigns/Hypotheses/Experiments/Factors/Models; Strategies/Backtests/Validation/Compare; Forward/Paper Trading/Champion-Challenger/Incidents; System/Data/Agent Runs/System Health.

- [ ] Add browser tests for keyboard navigation, dark/light contrast, responsive workstation layout, job progress states, and no direct database/client-side metric calculation.
- [ ] Run npm test -- --runInBand and npm run typecheck from apps/web; expected failure is missing app.
- [ ] Implement restrained dark-first shell with light support and generated typed API client.
- [ ] Run npm test -- --runInBand, npm run typecheck, and npm run lint; expected all pass.
- [ ] Commit: feat(web): add accessible QuantLab research shell

## Task M8.4: Campaign, experiment, evidence, and decision-trace views

**Files:** Create apps/web/app/research/campaigns/[id]/page.tsx, app/research/experiments/[id]/page.tsx, components/evidence-card.tsx, experiment-tabs.tsx, decision-trace.tsx, metric-with-provenance.tsx, rejected-trials.tsx; tests/web/campaign.spec.ts, experiment.spec.ts, provenance.spec.ts.

**Interfaces:** Campaign page shows hypothesis/falsification/progress/lineage/budget/critic; experiment tabs are Overview/Performance/Factors/Portfolio/Execution/Robustness/Data/Audit; every metric renders definition, assumption, artifact path, and calculator version.

- [ ] Test rejected trials remain visible, metric provenance opens source artifact metadata, decision trace follows Dataset→Feature/Factor→Model→Portfolio reason→Risk→Order→Fill, and validity/warnings cannot be hidden.
- [ ] Run named web tests; expected failure is missing views.
- [ ] Implement artifact-centric pages with chat secondary and no UI-side verdict calculation.
- [ ] Run named web tests; expected all pass.
- [ ] Commit: feat(web): visualize experiment evidence and lineage

## Task M8.5: Quant visualizations, paper/system health, and frozen demo mode

**Files:** Create components/charts/equity.tsx, drawdown.tsx, rank-ic.tsx, factor-correlation.tsx, folds.tsx, exposures.tsx, parameter-surface.tsx, cost-sensitivity.tsx, bootstrap.tsx, trial-context.tsx, paper-divergence.tsx; app/forward/paper/page.tsx, app/system/data/page.tsx, app/system/health/page.tsx, app/demo/[case]/page.tsx; tests/web/charts.spec.ts, paper.spec.ts, health.spec.ts, demo-security.spec.ts.

**Interfaces:** Charts consume backend artifact series with metric/version metadata. Demo mode accepts only allowlisted frozen artifact ids and is read-only with no paper credentials/controls.

- [ ] Test representative charts against fixed API fixtures, accessible labels/tooltips/tables, stale/coverage/incidents/readiness, champion/challenger status, frozen demo allowlist, disabled mutations, and credential/control non-reachability.
- [ ] Run named web tests; expected failure is missing views/charts.
- [ ] Implement required visualization and system pages; avoid decorative/neon trading-dashboard semantics.
- [ ] Run web unit/component/e2e tests and production build; expected all pass.
- [ ] Commit: feat(web): deliver auditable research and system views

## M8 Gate

Run:

~~~bash
python -m pytest tests/api tests/cli -q
cd apps/web && npm ci && npm run lint && npm run typecheck && npm test -- --runInBand && npm run build
cd ../..
python scripts/check_openapi_web_types.py
python scripts/verify_milestone.py M8 --require-prior
~~~

Acceptance: a new user can discover what was researched, exact dataset/model, OOS/lockbox status, all trials, cost/parameter robustness, paper evidence, and metric provenance without source inspection. Long jobs are persisted, public demo is frozen/read-only, and frontend has no quant authority. Commit checkpoint: chore(gate): accept M8.

# M9 — Flagship Release

## Task M9.1: Full frozen-data acceptance workflow

**Files:** Create configs/releases/quantlab-v1.yaml, scripts/run_v1_acceptance.py, tests/e2e/test_v1_acceptance.py, artifacts/golden/v1-acceptance/manifest.json, docs/research/quality-momentum-case-study.md.

**Interfaces:** AcceptanceRunner executes PIT Dataset→Universe→Factors→Composite+ML→Portfolio→Authoritative Backtest→Validation→Paper Candidate→Simulated Forward Sessions→Agent Campaign→Grounded Report and emits one content-addressed ReleaseEvidence manifest.

- [ ] Add fixture-defined expected stage ids, hashes/tolerances, validity/verdict, trial counts, prediction splits, order/fill counts, paper idempotency, and verified report claims.
- [ ] Run python -m pytest tests/e2e/test_v1_acceptance.py -q with network blocked; expected failure is missing runner/release fixture.
- [ ] Implement orchestration by composing milestone services; no release-only quant logic.
- [ ] Run acceptance twice in clean worktrees/containers; expected matching authoritative hashes.
- [ ] Commit: test(release): add frozen QuantLab V1 acceptance workflow

## Task M9.2: ADRs, calculator documentation, runbooks, and installation

**Files:** Create docs/decisions/0001-custom-core.md through 0010-security-boundaries.md for every ADR listed in spec §1.6; docs/installation.md, reproducibility.md, data-limitations.md, security.md, architecture.md; docs/runbooks/restore.md, incident-response.md, dataset-recovery.md; tests/docs/test_required_docs.py, test_commands.py.

**Interfaces:** Documentation records decision/context/consequences, exact supported Python/Docker commands, free-data limitations, pre-tax assumptions, modeled cost labels, backup/restore checks, and incident ownership.

- [ ] Test all required ADR ids exist, commands parse/run in a clean container, links resolve, metric definitions have calculator versions, and forbidden profit/proven language is absent from release claims.
- [ ] Run named docs tests; expected failure is missing documents.
- [ ] Write exact reproducible instructions and observed flagship evidence/limitations, not aspirational claims.
- [ ] Run named docs tests; expected all pass.
- [ ] Commit: docs: complete QuantLab architecture and operations handoff

## Task M9.3: Security, recovery, fault injection, and performance budgets

**Files:** Create quantlab/infrastructure/secrets.py, safe_artifacts.py; scripts/security_scan.py, restore_drill.py, benchmark_release.py; tests/security/test_secrets.py, test_safe_artifacts.py, test_untrusted_models.py, tests/faults/test_provider_timeout.py, test_db_outage.py, test_disk_failure.py, test_worker_termination.py, test_partial_dataset.py; configs/performance-budgets-v1.yaml.

**Interfaces:** SecretProvider returns opaque values and redacts logs; SafeArtifactResolver accepts ids, not paths; release benchmark records environment/dataset/worker counts and fails only against reviewed generous regression budgets.

- [ ] Test path traversal, unsafe deserialization, prompt-originated file ids, secret leaks, public DB exposure config, provider timeout, DB outage, disk failure, worker kill, duplicate callback, malformed/stale data, missing model, broker timeout, partial dataset invisibility, and successful restore drill.
- [ ] Run security/fault tests; expected failure is any unhandled scenario.
- [ ] Harden root causes while preserving M0–M8 behavior; benchmark factor/backtest/validation and document measured budgets.
- [ ] Rerun security/fault tests, restore drill, and benchmark; expected all pass within reviewed limits.
- [ ] Commit: fix(release): harden security recovery and performance

## Task M9.4: Three reliable public demonstrations and release packaging

**Files:** Create configs/demos/quality-momentum.yaml, etf-tactical.yaml, red-team.yaml; scripts/build_demo_bundle.py, verify_release.py; docs/demo-script.md, release-checklist.md; tests/e2e/test_demo_bundles.py, test_release_package.py; .github/workflows/release.yml.

**Interfaces:** Each demo bundle contains frozen allowlisted data/artifacts, a manifest/hash, read-only UI inputs, and no secrets/operational endpoints. ETF demo uses curated ETF universe and remains secondary; red team contains all three cases.

- [ ] Test clean offline install, manifest integrity, all demo routes, no mutation/control/credential reachability, and exact case-study artifact references.
- [ ] Run named tests; expected failure is missing bundles/release verifier.
- [ ] Build packages from a clean Git SHA; CI release must require M0–M9 gates and all critical/high issues closed.
- [ ] Run python scripts/verify_release.py --config configs/releases/quantlab-v1.yaml --offline; expected PASS.
- [ ] Commit: chore(release): package QuantLab V1 flagship demos

## M9 Gate

Run from a clean clone/worktree with no provider credentials:

~~~bash
python -m pip install -e ".[dev]"
QUANTLAB_OFFLINE=1 python scripts/run_v1_acceptance.py --config configs/releases/quantlab-v1.yaml
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy quantlab apps
cd apps/web && npm ci && npm run lint && npm run typecheck && npm test -- --runInBand && npm run build
cd ../..
python scripts/security_scan.py
python scripts/restore_drill.py --fixture synthetic_v1
python scripts/verify_release.py --config configs/releases/quantlab-v1.yaml --offline
python scripts/verify_milestone.py M9 --require-prior
~~~

Acceptance: all quant-critical tests pass; full frozen-data workflow and three demos run offline; release manifest is reproducible, grounded, secure, and contains no critical/high correctness issue. Commit checkpoint: chore(gate): accept M9. Create a release tag only after explicit human authorization; this plan does not authorize publishing/deployment.

---

## Milestone Acceptance Matrix

| Gate | Must exist | Must not exist/be used | Decisive evidence |
|---|---|---|---|
| M0 | contracts, quality tooling, storage, fixtures, doctor | factor/ML/agent/UI work | offline CI + architecture gate |
| M1 | PUBLISHED immutable PIT dataset | future/restated substitution | historical universe/fundamental canaries |
| M2 | reviewed factors and simple composite | ML model in baseline | golden rankings + reproducible research |
| M3 | authoritative event engine/accounting | same-close or vector authority | golden replay + conservation |
| M4 | lockbox, trial ledger, robustness | LLM verdict override | three red-team outcomes |
| M5 | purged OOS Ridge/LightGBM comparison | TRAIN portfolio input | leakage/label-shuffle/OOS gates |
| M6 | immutable forward evidence/recovery | active challenger/direct agent orders | crash matrix + reconciliation |
| M7 | typed budgeted grounded agents/MCP | shell/SQL/metric invention | permission and claim-verifier suite |
| M8 | API/CLI/auditable web/demo | UI quant truth or demo controls | provenance UX + production build |
| M9 | clean offline release workflow | unverified/published side effects | release evidence manifest |

## Commit and Review Discipline

- Use the checkpoint messages exactly as written unless repository convention established before M0 requires a documented equivalent.
- One checkpoint contains only the task's files plus directly required generated lock/migration files.
- Never commit a failing narrow test, a dirty milestone PASS artifact, credentials, mutable latest-data outputs, or unreviewed golden changes.
- Before every gate, review git diff from the prior accepted gate and confirm no premature package/dependency appeared.
- Any critical/high quant bug reopens the earliest affected milestone, adds a regression test there, invalidates downstream gate evidence, and requires rerunning all dependent gates.
- Branch merge, push, release tag, external deployment, and real-paper-broker connection require separate human authorization.

## Golden-Test Change Protocol

When a golden test fails:

1. Preserve the observed failure and identify whether code, fixture, formula, calendar, or approved spec changed.
2. Recompute the expected value independently with a human-computable derivation or a separately reviewed reference implementation.
3. Add docs/changes/quant-behavior/YYYY-MM-DD-description.md with old/new values, cause, affected calculators/artifacts, backward-compatibility impact, and reviewer approval.
4. Change expected golden data in a dedicated commit separate from implementation.
5. Rerun the earliest affected milestone plus all downstream gates. A snapshot-update command may not be the only evidence.

## Scope-Creep and Premature-Work Checks

Each gate runs scripts/check_scope.py MN. Required failures include:

- apps/web or Node dependencies before M8;
- apps/mcp, quantlab/agents, LLM dependencies before M7;
- quantlab/ml or LightGBM dependency used by M0–M4 authoritative paths;
- broker live endpoints, leverage/short/derivative/crypto/intraday types, RL/deep-price-model packages, Kubernetes/Spark manifests, agent-swarm frameworks, or unrestricted execution tools anywhere in V1;
- internet access in authoritative backtest/validation or gate verification;
- numeric fields sourced from agent prose or frontend calculations;
- golden output rewriting without an approved behavior-change record.

## Spec Coverage Review

| Approved spec section | Implementation coverage |
|---|---|
| §0 scope/principles | Global constraints, every gate, M9 evidence |
| §1 architecture/domain/ADRs | M0.2, target map, M9.2 |
| §2 PIT data/universe/manifests/quality | M1.1–M1.6 |
| §3 factors/transforms/evaluation/safe spec | M2.1–M2.5 and M7.1 safe factor specification |
| §4 ML/walk-forward/OOS | M5.1–M5.5 |
| §5 portfolio/risk/capacity | M3.1–M3.2 |
| §6 event backtest/execution/accounting/metrics | M3.3–M3.6 |
| §7 falsification/lockbox/trials/statistics | M4.1–M4.5 |
| §8 paper/recovery/reconciliation/evidence | M6.1–M6.5 |
| §9 agents/tools/MCP/grounding | M7.1–M7.5 |
| §10 API/CLI/web/demo UX | M8.1–M8.5 |
| §11 infrastructure/jobs/telemetry/security/recovery | M0.3–M0.5, M6.1, M8.1, M9.2–M9.3 |
| §12 testing/golden/fault/quality gates | Global execution and golden protocols plus every milestone test suite |
| §13 M0–M9 acceptance | Ten explicit milestone gates and acceptance matrix |
| §14 implementation guardrails | Global constraints, scope checker, gate verifier |
| §15 technology defaults | Header stack, M0 lock, M8 web lock |
| §16 flagship research case | M7.5, M9.1, M9.4 |
| §17 V1 success | M9.1 and M9 gate |
| §18 handoff sequence | README, CODEX_HANDOFF.md, this plan, approval requirement |

Self-review outcome: all approved sections are mapped; public interfaces used across milestones are defined in the interface ledger or in the producing task; commands referenced by gates have a creating task; stretch features are outside the critical path; unfinished-marker and weak-instruction scans must return no matches before this plan is approved.

## Plan Completion Checklist

- [x] Spec §§0–18 map to at least one task or global constraint.
- [x] M0–M9 gates are sequential, executable, and reject stale/missing prior evidence.
- [x] Every task names files, interfaces, failing tests, passing tests, verification, and a commit checkpoint.
- [x] PIT, no-lookahead, OOS, lockbox, accounting, immutability, recovery, permissions, and claim-grounding invariants have explicit negative tests.
- [x] Dashboard and autonomous agent work cannot begin early.
- [x] No stretch goal blocks M9.
- [x] No implementation action is authorized by this planning artifact itself; execution starts only after plan approval.

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
