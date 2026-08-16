from __future__ import annotations


class QuantLabError(Exception):
    """Base exception for deterministic QuantLab failures."""


class ConfigError(QuantLabError):
    """Raised when configuration cannot be parsed or validated."""
