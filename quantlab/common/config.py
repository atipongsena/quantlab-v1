from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from quantlab.common.errors import ConfigError

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | dict[str, "JsonValue"] | list["JsonValue"]
SECRET_MARKER = "***REDACTED***"
SECRET_NAME_PARTS = ("secret", "token", "password", "api_key", "apikey", "key")


@dataclass(frozen=True, slots=True)
class AppConfig:
    environment: str
    timezone: str
    data_dir: Path
    artifact_dir: Path
    log_level: str
    secrets: MappingProxyType[str, str]

    def redacted(self) -> dict[str, JsonValue]:
        return cast(
            dict[str, JsonValue],
            redact_secrets(
                {
                    "environment": self.environment,
                    "timezone": self.timezone,
                    "data_dir": str(self.data_dir),
                    "artifact_dir": str(self.artifact_dir),
                    "log_level": self.log_level,
                    "secrets": dict(self.secrets),
                }
            ),
        )


def load_config(paths: Sequence[Path], env: Mapping[str, str]) -> AppConfig:
    merged: dict[str, JsonValue] = {}
    for path in paths:
        _merge_dicts(merged, _read_config(path))
    _merge_dicts(merged, _env_overrides(env))

    required = ("environment", "timezone", "data_dir", "artifact_dir", "log_level")
    missing = [name for name in required if name not in merged]
    if missing:
        raise ConfigError(f"missing required config: {', '.join(missing)}")

    secrets_value = merged.get("secrets", {})
    if not isinstance(secrets_value, dict):
        raise ConfigError("secrets must be a mapping")
    secrets = {
        str(key): _require_string(value, f"secrets.{key}") for key, value in secrets_value.items()
    }

    return AppConfig(
        environment=_require_string(merged["environment"], "environment"),
        timezone=_require_string(merged["timezone"], "timezone"),
        data_dir=Path(_require_string(merged["data_dir"], "data_dir")),
        artifact_dir=Path(_require_string(merged["artifact_dir"], "artifact_dir")),
        log_level=_require_string(merged["log_level"], "log_level"),
        secrets=MappingProxyType(secrets),
    )


def redact_secrets(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        redacted: dict[str, JsonValue] = {}
        for key, item in value.items():
            if _is_secret_name(key):
                redacted[key] = SECRET_MARKER
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def _read_config(path: Path) -> dict[str, JsonValue]:
    if not path.exists():
        raise ConfigError(f"config path does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = _parse_yaml_subset(stripped)
    if not isinstance(parsed, dict):
        raise ConfigError("config root must be a mapping")
    return cast(dict[str, JsonValue], parsed)


def _parse_yaml_subset(text: str) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    current_mapping: dict[str, JsonValue] | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if ":" not in raw_line:
            raise ConfigError(f"unsupported config line: {raw_line}")
        key, raw_value = raw_line.strip().split(":", 1)
        value = raw_value.strip()
        if indent == 0:
            if value == "":
                nested: dict[str, JsonValue] = {}
                result[key] = nested
                current_mapping = nested
            else:
                result[key] = _parse_scalar(value)
                current_mapping = None
        elif indent == 2 and current_mapping is not None:
            current_mapping[key] = _parse_scalar(value)
        else:
            raise ConfigError(f"unsupported indentation in config line: {raw_line}")
    return result


def _parse_scalar(value: str) -> JsonValue:
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.isdecimal() or (value.startswith("-") and value[1:].isdecimal()):
        return int(value)
    return value.strip("\"'")


def _merge_dicts(target: dict[str, JsonValue], source: dict[str, JsonValue]) -> None:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _merge_dicts(existing, value)
        else:
            target[key] = value


def _env_overrides(env: Mapping[str, str]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    mapping = {
        "QUANTLAB_ENVIRONMENT": "environment",
        "QUANTLAB_TIMEZONE": "timezone",
        "QUANTLAB_DATA_DIR": "data_dir",
        "QUANTLAB_ARTIFACT_DIR": "artifact_dir",
        "QUANTLAB_LOG_LEVEL": "log_level",
    }
    for env_name, config_name in mapping.items():
        if env_name in env:
            result[config_name] = env[env_name]
    secrets: dict[str, JsonValue] = {}
    for env_name, value in env.items():
        prefix = "QUANTLAB_SECRET_"
        if env_name.startswith(prefix):
            secrets[env_name.removeprefix(prefix).lower()] = value
    if secrets:
        result["secrets"] = secrets
    return result


def _require_string(value: JsonValue, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{field_name} must be a nonempty string")
    return value


def _is_secret_name(name: str) -> bool:
    normalized = name.lower()
    if normalized == "secrets":
        return False
    return any(part in normalized for part in SECRET_NAME_PARTS)
