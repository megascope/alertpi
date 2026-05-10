from __future__ import annotations

import hashlib
import hmac
from time import time

from fastapi.testclient import TestClient

from siren_driver.main import create_app


def _sign(secret: str, timestamp: int, body: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def test_trigger_rejects_missing_auth(monkeypatch):
    monkeypatch.setenv("SIREN_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    with TestClient(app) as client:
        response = client.post("/trigger", json={"duration_seconds": 1})

    assert response.status_code == 401


def test_trigger_accepts_valid_signature(monkeypatch):
    monkeypatch.setenv("SIREN_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    body = "{\"duration_seconds\":1}"
    timestamp = int(time())

    with TestClient(app) as client:
        response = client.post(
            "/trigger",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Siren-Timestamp": str(timestamp),
                "X-Siren-Signature": _sign("secret", timestamp, body),
            },
        )

    assert response.status_code == 202
