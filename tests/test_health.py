from fastapi.testclient import TestClient

from app.api.main import app
from app.config.constants import HEALTH_STATUS_OK

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == HEALTH_STATUS_OK
