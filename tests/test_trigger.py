from __future__ import annotations

from fastapi.testclient import TestClient

from siren_driver.main import create_app


def test_trigger_uses_default_duration(monkeypatch):
    monkeypatch.setenv("SIREN_BEARER_TOKEN", "secret")
    monkeypatch.setenv("SIREN_TRIGGER_DURATION_SECONDS", "2")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/trigger",
            json={},
            headers={
                "Authorization": "Bearer secret",
            },
        )

    assert response.status_code == 202
    assert response.json()["duration_seconds"] == 2


def test_trigger_rejects_non_finite_duration(monkeypatch):
    monkeypatch.setenv("SIREN_BEARER_TOKEN", "secret")
    monkeypatch.setenv("GPIOZERO_PIN_FACTORY", "mock")
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/trigger",
            data='{"duration_seconds": NaN}',
            headers={
                "Authorization": "Bearer secret",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 422
