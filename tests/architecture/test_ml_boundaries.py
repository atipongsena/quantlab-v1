"""Tests enforcing architecture boundaries for ML package."""

import inspect

import quantlab.factors
import quantlab.ml


def test_factor_engine_does_not_depend_on_ml() -> None:
    # Assert factor engine does not import ml modules
    factor_src = inspect.getsource(quantlab.factors)
    assert "quantlab.ml" not in factor_src


def test_ml_package_isolated_from_broker_and_live() -> None:
    ml_src = inspect.getsource(quantlab.ml)
    assert "broker" not in ml_src
    assert "live_money" not in ml_src
