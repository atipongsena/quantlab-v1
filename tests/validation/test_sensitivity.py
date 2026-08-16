"""Tests for parameter sensitivity surface analysis."""

from quantlab.validation.sensitivity import ParameterTopology, SensitivityCell, SensitivitySurface


def test_sensitivity_surface_plateau_vs_spike() -> None:
    # Plateau: smooth neighboring Sharpe ratios
    plateau_cells = [
        SensitivityCell({"top_k": 20}, 1.20, 0.15, 0.10),
        SensitivityCell({"top_k": 30}, 1.25, 0.16, 0.10),
        SensitivityCell({"top_k": 50}, 1.18, 0.14, 0.10),
    ]
    surface = SensitivitySurface.analyze("top_k", plateau_cells)
    assert surface.topology == ParameterTopology.PLATEAU

    # Spike: sharp isolated peak
    spike_cells = [
        SensitivityCell({"lookback": 10}, 0.50, 0.05, 0.20),
        SensitivityCell({"lookback": 20}, 2.00, 0.30, 0.05),
        SensitivityCell({"lookback": 30}, 0.40, 0.04, 0.25),
    ]
    spike_surface = SensitivitySurface.analyze("lookback", spike_cells)
    assert spike_surface.topology == ParameterTopology.SPIKE
