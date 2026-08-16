"""LLM client interface and deterministic offline mock client."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Protocol for LLM interactions."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str: ...


class FakeLLMClient:
    """Deterministic mock LLM client for offline reproducible research campaigns."""

    def __init__(self, mode: str = "default") -> None:
        self.mode = mode

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        prompt_lower = prompt.lower()
        if "idea" in prompt_lower or "hypothesize" in prompt_lower:
            return (
                "Hypothesis: High ROE Quality stocks filter out low-quality momentum traps, "
                "yielding superior risk-adjusted returns and higher Information Ratio."
            )
        if "factor_engineer" in prompt_lower or "code" in prompt_lower:
            return (
                "Factor Spec: 0.60 * zscore(momentum_12_1) + 0.40 * zscore(quality_roe). "
                "Vector implementation achieves Sharpe 1.45, Rank IC 0.058."
            )
        if "critic" in prompt_lower or "falsify" in prompt_lower:
            return (
                "Critic Assessment: No lookahead leakage detected in PIT alignment. "
                "Sensitivity surface is monotonic across lookback parameters [6M..12M]. "
                "Deflated Sharpe DSR = 0.91 (passes >0.80 multiple testing threshold)."
            )
        if "strategist" in prompt_lower or "verdict" in prompt_lower:
            return (
                "Verdict: VALIDATED. Promoted to PAPER_CANDIDATE. "
                "Hypothesis successfully verified across 5-fold walk-forward validation."
            )
        return "Deterministic research response."
