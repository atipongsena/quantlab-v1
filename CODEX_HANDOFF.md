# Codex Handoff Protocol

## Approval status

- Master design: approved.
- Detailed implementation plan: approved on 2026-08-16.
- Selected workflow: Superpowers Subagent-Driven Development, one milestone at a time.
- Implementation status: not started. Begin only after an explicit instruction to start M0.
- Required preflight: establish a Git repository and documentation baseline, then use superpowers:using-git-worktrees to create or verify an isolated feature worktree.

## Mission

Build **QuantLab V1** exactly from the master design specification, preserving scientific validity, reproducibility, architectural boundaries, and test gates.

## Required first action

Read the master design spec completely:

`docs/superpowers/specs/2026-08-16-quantlab-v1-design.md`

Then read the detailed implementation plan completely:

`docs/superpowers/plans/2026-08-16-quantlab-v1-implementation.md`

The plan is approved for execution. After an explicit instruction to start M0, follow its Approved Execution Method, task briefs, reviews, and milestone gates exactly; do not scaffold the whole product in one pass.

## Non-negotiable rules

1. Do not advance to the next milestone until the current milestone's acceptance tests pass.
2. A task is not complete because code exists; the specified behavior, tests, documentation, and reproducibility requirements must also be satisfied.
3. Use deterministic domain logic for data timing, factors, labels, portfolio construction, risk, execution, accounting, metrics, validation, and paper-trading safety. Never replace these with LLM reasoning.
4. Do not let an LLM invent, modify, or override quantitative metrics or authoritative artifacts.
5. Do not add frameworks, services, asset classes, or features outside V1 unless the implementation plan explicitly promotes them.
6. Do not update golden expected results merely to make tests pass. First identify and document the behavioral change.
7. Authoritative historical backtests and validation must be offline-capable and operate on frozen/versioned datasets.
8. Preserve point-in-time semantics. A value is usable only when `available_at <= decision_time`.
9. Signal generation after an EOD close may not fill at that same close under the default execution model. Default execution is next eligible session open plus configured costs/slippage.
10. Only out-of-sample predictions may enter authoritative ML portfolio backtests.
11. A consumed holdout is never “unseen” again for a revised candidate.
12. Failed and rejected experiments remain in the research ledger.
13. Research agents do not receive direct broker-order submission capability or unrestricted shell/SQL/Python execution in the standard runtime.
14. Paper scheduler/jobs must be idempotent, recoverable, and reconciled before retrying uncertain broker submissions.
15. Public/demo mode must use frozen artifacts and must not expose paper credentials or operational controls.

## Build order

Follow the milestone sequence in the master spec:

- M0 Engineering Foundation
- M1 Point-in-Time Data
- M2 Factor Research
- M3 Portfolio + Event-Driven Backtest
- M4 Validation & Falsification
- M5 ML Ranking
- M6 Paper Trading & Forward Evidence
- M7 Agentic Research + MCP
- M8 API + Research Dashboard
- M9 Flagship Release

Do not build the full dashboard before M8 and do not build the autonomous research agent before M7.

## Working style for Codex

For each milestone:

- Restate the milestone objective and acceptance criteria.
- Identify the smallest coherent vertical slice.
- Write tests before or alongside implementation for all new behavior.
- Keep files focused and dependencies pointing inward toward domain/core.
- Run the milestone's full verification suite before claiming completion.
- Report exactly what changed, commands run, test results, remaining warnings, and any deliberate deviation from the spec.
- If the design is ambiguous, stop and surface the ambiguity rather than silently inventing architecture.

For each implementation task, use one fresh implementer, then an independent reviewer. Do not run implementation agents in parallel. Split oversized tasks according to the approved plan without weakening the parent acceptance criteria.

## Definition of success

QuantLab V1 is successful when it can take a point-in-time dataset through factor research, a deterministic baseline and ML challenger, portfolio construction, authoritative event-driven backtesting, falsification/robustness, paper forward testing, and grounded agentic research—while keeping every quantitative conclusion reproducible and auditable.
