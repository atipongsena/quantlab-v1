from __future__ import annotations

from pathlib import Path

import pytest

from quantlab.common.config import ConfigError, load_config, redact_secrets


def test_config_precedence_and_secret_redaction(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    override = tmp_path / "test.yaml"
    base.write_text(
        """
environment: base
timezone: UTC
data_dir: data/base
artifact_dir: artifacts/base
log_level: INFO
secrets:
  provider_api_key: base-secret
""",
        encoding="utf-8",
    )
    override.write_text(
        """
environment: test
data_dir: data/test
""",
        encoding="utf-8",
    )

    config = load_config(
        (base, override),
        {
            "QUANTLAB_LOG_LEVEL": "DEBUG",
            "QUANTLAB_SECRET_PROVIDER_API_KEY": "env-secret",
        },
    )

    assert config.environment == "test"
    assert config.timezone == "UTC"
    assert config.data_dir == Path("data/test")
    assert config.artifact_dir == Path("artifacts/base")
    assert config.log_level == "DEBUG"
    assert config.secrets["provider_api_key"] == "env-secret"
    assert config.redacted()["secrets"] == {"provider_api_key": "***REDACTED***"}


def test_config_rejects_missing_required_fields(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("environment: test\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="missing required config"):
        load_config((bad,), {})


def test_redact_secrets_handles_nested_values() -> None:
    redacted = redact_secrets(
        {
            "api_key": "secret",
            "nested": {"token": "secret", "safe": "value"},
            "items": [{"password": "secret"}],
        }
    )

    assert redacted == {
        "api_key": "***REDACTED***",
        "nested": {"token": "***REDACTED***", "safe": "value"},
        "items": [{"password": "***REDACTED***"}],
    }
