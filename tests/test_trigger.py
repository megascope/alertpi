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
