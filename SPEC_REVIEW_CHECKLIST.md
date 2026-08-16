# QuantLab V1 — Written Spec Review Checklist

**Review outcome:** Approved on 2026-08-16. The detailed M0–M9 implementation plan is approved, and Subagent-Driven Development is selected for future execution. Implementation has not started.

Before authorizing the implementation plan, confirm that the master specification matches the intended product on these points:

- V1 remains US equities + ETFs, Daily/EOD, long-only, free-first.
- Historical equity research uses a point-in-time liquidity universe rather than today's index membership.
- Point-in-time `available_at` semantics are mandatory for fundamentals and other revised data.
- Simple multi-factor baseline is built before ML and remains a valid champion if ML does not add robust OOS value.
- Authoritative execution is next eligible session open by default; no same-close look-ahead.
- Portfolio, risk, accounting, metrics, validation, and paper safeguards are deterministic.
- Validation includes lockbox discipline, robustness, costs, trial ledger, and red-team strategies.
- Paper trading creates immutable forward predictions and has idempotency/recovery/reconciliation safeguards.
- Research agents use typed tools, budgets, permissions, and grounded metric claims; no direct arbitrary paper orders.
- Dashboard and autonomous agents are intentionally delayed until the core quant pipeline is verified.
- Milestones M0–M9 and their acceptance gates are the required build order.
- No V1 scope creep into live money, intraday, derivatives, crypto, shorting, leverage, RL, Kubernetes, or agent swarms.

If these points are approved, the next step is a detailed implementation plan derived from the master spec.
