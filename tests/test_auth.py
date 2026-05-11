from __future__ import annotations

from fastapi.testclient import TestClient

from siren_driver.main import create_app


def test_trigger_rejects_missing_auth(monkeypatch):
    monkeypatch.setenv("SIREN_BEARER_TOKEN", "secret")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    with TestClient(app) as client:
        response = client.post("/trigger", json={"duration_seconds": 1})

    assert response.status_code == 401


def test_trigger_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("SIREN_BEARER_TOKEN", "secret")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/trigger",
            json={"duration_seconds": 1},
            headers={
                "Authorization": "Bearer secret",
            },
        )

    assert response.status_code == 202
