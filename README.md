# QuantLab V1 — Design Handoff Package

This package contains the approved system design for **QuantLab V1**, a reproducible, point-in-time-aware, agentic quantitative research and paper-trading platform for US equities and ETFs.

## Start here

1. Read `docs/superpowers/specs/2026-08-16-quantlab-v1-design.md` in full.
2. Read `CODEX_HANDOFF.md` before asking Codex to take any implementation action.
3. Read the approved plan at `docs/superpowers/plans/2026-08-16-quantlab-v1-implementation.md`.
4. The plan was approved on 2026-08-16 with **Subagent-Driven Development** selected as the execution workflow.
5. Do **not** begin implementation until the user explicitly instructs Codex to start M0; first create/verify the required Git repository and isolated worktree.

## Design principles

- **Agent proposes. Quant engine proves.**
- **Every number must be reproducible and traceable.**
- **A strategy earns promotion by surviving falsification, not by having the prettiest backtest.**
- Quant logic, risk limits, accounting, validation gates, and paper-trading safeguards are deterministic.
- V1 is intentionally narrow: US equities + ETFs, Daily/EOD, long-only, free-first data, research + backtest + paper trading.

## Repository status

This handoff repository contains the approved design and approved detailed M0–M9 implementation plan. It intentionally contains no QuantLab implementation code. The selected future execution method is milestone-bounded Subagent-Driven Development with independent task and milestone reviews.
