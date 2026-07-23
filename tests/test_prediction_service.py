import torch
from PIL import Image

from app.config.model_config import config
from app.models.resnet import build_model
from app.services.prediction_service import CLASS_NAMES, PredictionService


def test_predict_returns_probability_per_class(tmp_path):
    weights_path = tmp_path / "model.pth"
    torch.save(build_model(config["model"]["num_classes"], pretrained=False).state_dict(), weights_path)

    image_path = tmp_path / "xray.png"
    Image.new("RGB", (224, 224), color=(100, 100, 100)).save(image_path)

    service = PredictionService(weights_path=str(weights_path), device="cpu")
    result = service.predict(str(image_path))

    assert set(result.keys()) == set(CLASS_NAMES)
    assert all(0.0 <= p <= 1.0 for p in result.values())
