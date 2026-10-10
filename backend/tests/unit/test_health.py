from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_reports_service_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "slotback-api"}
