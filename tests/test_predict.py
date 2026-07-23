import torch
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.api.routes.predict import get_prediction_service
from app.config.model_config import config
from app.config.settings import settings
from app.core.dependencies import get_db
from app.database import patient_model, prediction_model, user_model  # noqa: F401
from app.database.base import Base
from app.database.patient_model import Patient, Study
from app.database.prediction_model import Prediction
from app.models.resnet import build_model


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
    get_prediction_service.cache_clear()
    yield TestClient(app), TestSessionLocal
    app.dependency_overrides.clear()
    get_prediction_service.cache_clear()


def _make_study(TestSessionLocal, tmp_path) -> int:
    image_path = tmp_path / "xray.png"
    Image.new("RGB", (64, 64), color=(90, 90, 90)).save(image_path)

    db = TestSessionLocal()
    patient = Patient(external_id="patient-predict-1")
    db.add(patient)
    db.flush()
    study = Study(patient_id=patient.id, image_path=str(image_path))
    db.add(study)
    db.commit()
    study_id = study.id
    db.close()
    return study_id


def test_predict_returns_labels_and_gradcam(client, tmp_path, monkeypatch):
    test_client, TestSessionLocal = client
    weights_path = tmp_path / "model.pth"
    torch.save(build_model(config["model"]["num_classes"], pretrained=False).state_dict(), weights_path)
    monkeypatch.setattr(settings, "model_weights_path", str(weights_path))
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))

    study_id = _make_study(TestSessionLocal, tmp_path)

    response = test_client.post(f"/predict/{study_id}")

    assert response.status_code == 201
    body = response.json()
    assert body["study_id"] == study_id
    assert len(body["disease_labels"]) == config["model"]["num_classes"]
    assert body["report_text"] is None

    db = TestSessionLocal()
    assert db.query(Prediction).filter_by(study_id=study_id).count() == 1
    db.close()


def test_predict_404_for_missing_study(client):
    test_client, _ = client
    response = test_client.post("/predict/999")
    assert response.status_code == 404


def test_predict_503_without_trained_checkpoint(client, tmp_path, monkeypatch):
    test_client, TestSessionLocal = client
    monkeypatch.setattr(settings, "model_weights_path", str(tmp_path / "does-not-exist.pth"))

    study_id = _make_study(TestSessionLocal, tmp_path)

    response = test_client.post(f"/predict/{study_id}")

    assert response.status_code == 503


def test_predict_includes_report_text_when_llm_available(client, tmp_path, monkeypatch):
    import app.api.routes.predict as predict_route

    test_client, TestSessionLocal = client
    weights_path = tmp_path / "model.pth"
    torch.save(build_model(config["model"]["num_classes"], pretrained=False).state_dict(), weights_path)
    monkeypatch.setattr(settings, "model_weights_path", str(weights_path))
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))

    class _FakeReportService:
        def generate_report(self, findings):
            return "Fake narrative report."

    monkeypatch.setattr(predict_route, "get_report_service", lambda: _FakeReportService())

    study_id = _make_study(TestSessionLocal, tmp_path)

    response = test_client.post(f"/predict/{study_id}")

    assert response.status_code == 201
    assert response.json()["report_text"] == "Fake narrative report."

    db = TestSessionLocal()
    assert db.query(Prediction).filter_by(study_id=study_id).first().report_text == "Fake narrative report."
    db.close()
