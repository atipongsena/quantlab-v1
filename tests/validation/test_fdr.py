"""Tests for Benjamini-Hochberg FDR control."""

from quantlab.validation.fdr import BenjaminiHochbergFDR


def test_benjamini_hochberg_fdr_discovery() -> None:
    # 5 hypotheses with p-values
    p_values = [0.001, 0.005, 0.03, 0.20, 0.80]
    sig = BenjaminiHochbergFDR.adjust(p_values, alpha=0.05)

    assert sig[0] is True  # 0.001 is significant
    assert sig[1] is True  # 0.005 is significant
    assert sig[4] is False  # 0.80 is not significant
