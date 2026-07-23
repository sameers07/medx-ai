from PIL import Image

from app.config.model_config import config
from app.models.resnet import build_model
from app.services.gradcam_service import GradCAMService
from app.services.storage_service import StorageService


def test_generate_heatmap_saves_overlay(tmp_path):
    model = build_model(config["model"]["num_classes"], pretrained=False)

    image_path = tmp_path / "xray.png"
    Image.new("RGB", (224, 224), color=(100, 100, 100)).save(image_path)

    service = GradCAMService(storage_service=StorageService(base_dir=str(tmp_path / "storage")))
    heatmap_path = service.generate_heatmap(str(image_path), model, config["explainability"]["target_layer"])

    assert heatmap_path.endswith("xray_heatmap.png")
    saved = Image.open(heatmap_path)
    assert saved.size == (224, 224)
