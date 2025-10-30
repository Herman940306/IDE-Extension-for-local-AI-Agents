from fastapi.testclient import TestClient
from src.main import app as main_app


def test_api_status_endpoint_includes_core_sections() -> None:
    client = TestClient(main_app)

    response = client.get("/api/status")
    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] in {"ready", "degraded"}

    service = payload["service"]
    assert service["name"]
    assert service["uptime_seconds"] >= 0

    dependencies = payload["dependencies"]
    assert "ollama" in dependencies
    assert "redis" in dependencies
    assert "openai" in dependencies

    mode = payload["mode"]
    assert "current_mode" in mode

    jobs = payload["jobs"]
    assert "total" in jobs
    assert isinstance(jobs["total"], int)

    connections = payload["connections"]
    assert "active" in connections
