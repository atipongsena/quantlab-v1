"""Tests ensuring label runtime isolation from factor calculations."""

import inspect

import quantlab.factors


def test_factor_package_does_not_import_ml_labels() -> None:
    # Introspect factor module dependencies to assert no circular reference to ml labels
    factor_source = inspect.getsource(quantlab.factors)
    assert "labels" not in factor_source
    assert "forward_return" not in factor_source
