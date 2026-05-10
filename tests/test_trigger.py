from __future__ import annotations

import hashlib
import hmac
from time import time

from fastapi.testclient import TestClient

from siren_driver.main import create_app


def _signature(secret: str, timestamp: int, body: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.{body}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_trigger_uses_default_duration(monkeypatch):
    monkeypatch.setenv("SIREN_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("SIREN_TRIGGER_DURATION_SECONDS", "2")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    body = "{}"
    timestamp = int(time())

    with TestClient(app) as client:
        response = client.post(
            "/trigger",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Siren-Timestamp": str(timestamp),
                "X-Siren-Signature": _signature("secret", timestamp, body),
            },
        )

    assert response.status_code == 202
    assert response.json()["duration_seconds"] == 2
