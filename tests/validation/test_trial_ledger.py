"""Tests for append-only trial ledger."""

from quantlab.validation.trials import TrialLedger


def test_trial_ledger_record_and_idempotency() -> None:
    ledger = TrialLedger()

    spec = {"strategy": "strat_1", "window": 20}
    r1 = ledger.record_once("CAMP-01", "CAND-01", spec, observed_sharpe=1.2, observed_cagr=0.15)
    r2 = ledger.record_once("CAMP-01", "CAND-01", spec, observed_sharpe=1.2, observed_cagr=0.15)

    assert r1.trial_id == r2.trial_id
    assert ledger.total_trials == 1

    # New distinct trial spec
    spec2 = {"strategy": "strat_1", "window": 30}
    r3 = ledger.record_once("CAMP-01", "CAND-01", spec2, observed_sharpe=1.0, observed_cagr=0.12)
    assert ledger.total_trials == 2
    assert r3.trial_id != r1.trial_id
