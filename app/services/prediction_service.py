"""PredictionService — loads the trained ResNet-50 checkpoint and runs inference."""
import torch

from app.config.model_config import config
from app.config.settings import settings
from app.models.resnet import build_model
from app.services.image_service import ImageService

CLASS_NAMES: list[str] = config["model"]["class_names"]


class PredictionService:
    def __init__(self, weights_path: str | None = None, device: str | None = None):
        self.device = torch.device(device or settings.device)
        self.model = build_model(config["model"]["num_classes"], pretrained=False)
        state_dict = torch.load(
            weights_path or settings.model_weights_path, map_location=self.device, weights_only=True
        )
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        self.image_service = ImageService()

    def predict(self, image_path: str) -> dict[str, float]:
        """Returns {disease_label: probability} for every class in config.yaml."""
        image = self.image_service.preprocess(image_path).to(self.device)
        with torch.no_grad():
            logits = self.model(image)
        probs = torch.sigmoid(logits).squeeze(0).cpu().tolist()
        return dict(zip(CLASS_NAMES, probs))
