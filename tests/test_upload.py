import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.core.dependencies import get_db
from app.database import patient_model, prediction_model, user_model  # noqa: F401
from app.database.base import Base
from app.database.patient_model import Patient, Study


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSessionLocal
    app.dependency_overrides.clear()


def _fake_xray_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=(50, 50, 50)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_creates_patient_and_study(client):
    test_client, TestSessionLocal = client

    response = test_client.post(
        "/upload",
        files={"file": ("xray.png", _fake_xray_png(), "image/png")},
        data={"patient_external_id": "patient-001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "study_id" in body and "patient_id" in body

    db = TestSessionLocal()
    assert db.query(Patient).filter_by(external_id="patient-001").count() == 1
    assert db.query(Study).filter_by(id=body["study_id"]).count() == 1
    db.close()


def test_upload_reuses_existing_patient(client):
    test_client, TestSessionLocal = client

    for _ in range(2):
        response = test_client.post(
            "/upload",
            files={"file": ("xray.png", _fake_xray_png(), "image/png")},
            data={"patient_external_id": "patient-002"},
        )
        assert response.status_code == 201

    db = TestSessionLocal()
    assert db.query(Patient).filter_by(external_id="patient-002").count() == 1
    assert db.query(Study).count() == 2
    db.close()


def test_upload_rejects_invalid_extension(client):
    test_client, _ = client

    response = test_client.post(
        "/upload",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
        data={"patient_external_id": "patient-003"},
    )

    assert response.status_code == 400
