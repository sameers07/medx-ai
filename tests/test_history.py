import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.core.dependencies import get_db
from app.database import patient_model, prediction_model, user_model  # noqa: F401
from app.database.base import Base
from app.database.patient_model import Patient, Study
from app.database.prediction_model import Prediction


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


def test_history_returns_predictions_most_recent_first(client):
    test_client, TestSessionLocal = client
    db = TestSessionLocal()
    patient = Patient(external_id="patient-hist-1")
    db.add(patient)
    db.flush()
    study = Study(patient_id=patient.id, image_path="storage/uploads/x.png")
    db.add(study)
    db.flush()

    older = Prediction(study_id=study.id, disease_labels={"Pneumonia": 0.1}, gradcam_path="a.png")
    db.add(older)
    db.flush()
    newer = Prediction(study_id=study.id, disease_labels={"Pneumonia": 0.9}, gradcam_path="b.png")
    db.add(newer)
    db.commit()
    older_id, newer_id = older.id, newer.id
    db.close()

    response = test_client.get("/history/patient-hist-1")

    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == "patient-hist-1"
    assert [p["prediction_id"] for p in body["predictions"]] == [newer_id, older_id]


def test_history_empty_for_patient_with_no_predictions(client):
    test_client, TestSessionLocal = client
    db = TestSessionLocal()
    db.add(Patient(external_id="patient-hist-2"))
    db.commit()
    db.close()

    response = test_client.get("/history/patient-hist-2")

    assert response.status_code == 200
    assert response.json()["predictions"] == []


def test_history_404_for_unknown_patient(client):
    test_client, _ = client
    response = test_client.get("/history/does-not-exist")
    assert response.status_code == 404
