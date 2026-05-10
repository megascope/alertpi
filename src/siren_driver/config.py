from __future__ import annotations

from dataclasses import dataclass
import os


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _get_env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    webhook_secret: str
    gpio_pin: int = 17
    default_duration_seconds: float = 3.0
    max_duration_seconds: float = 10.0
    auth_skew_seconds: int = 300
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        webhook_secret = _get_env_str("SIREN_WEBHOOK_SECRET")
        if not webhook_secret:
            raise RuntimeError("SIREN_WEBHOOK_SECRET must be set")

        return cls(
            webhook_secret=webhook_secret,
            gpio_pin=_get_env_int("SIREN_GPIO_PIN", 17),
            default_duration_seconds=_get_env_float("SIREN_TRIGGER_DURATION_SECONDS", 3.0),
            max_duration_seconds=_get_env_float("SIREN_MAX_DURATION_SECONDS", 10.0),
            auth_skew_seconds=_get_env_int("SIREN_AUTH_SKEW_SECONDS", 300),
            host=_get_env_str("SIREN_HOST", "0.0.0.0"),
            port=_get_env_int("SIREN_PORT", 8000),
        )
