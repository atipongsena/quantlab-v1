"""Tests for candidate strategy freezing and fingerprinting."""

from quantlab.validation.candidate import CandidateFreezer


def test_candidate_freeze_deterministic_fingerprint() -> None:
    cfg = {
        "strategy_id": "top30-mom",
        "target_size": 30,
        "weighting": "equal",
    }
    c1 = CandidateFreezer.freeze("top30-mom", cfg, "git:abc1234")
    c2 = CandidateFreezer.freeze("top30-mom", cfg, "git:abc1234")

    assert c1.candidate_id == c2.candidate_id
    assert c1.config_hash == c2.config_hash
    assert c1.code_fingerprint == "git:abc1234"
