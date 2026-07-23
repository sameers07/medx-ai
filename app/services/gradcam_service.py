"""GradCAMService — Grad-CAM heatmap generation over the trained ResNet-50's target layer."""
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

from app.preprocessing.transforms import get_transforms
from app.services.storage_service import StorageService

_eval_transform = get_transforms(train=False)


def resolve_target_layer(model: nn.Module, target_layer: str | nn.Module) -> nn.Module:
    """`target_layer` is a config.yaml name like "layer4" (its last block) or a module directly."""
    if isinstance(target_layer, nn.Module):
        return target_layer
    layer = getattr(model, target_layer)
    return layer[-1] if isinstance(layer, nn.Sequential) else layer


class GradCAMService:
    def __init__(self, storage_service: StorageService | None = None):
        self.storage_service = storage_service or StorageService()

    def generate_heatmap(self, image_path: str, model: nn.Module, target_layer: str | nn.Module) -> str:
        """Runs Grad-CAM for the model's top predicted class and saves an overlay PNG.

        Returns the saved heatmap's path.
        """
        model.eval()
        layer = resolve_target_layer(model, target_layer)

        original = Image.open(image_path).convert("RGB")
        input_tensor = _eval_transform(original).unsqueeze(0)

        with torch.no_grad():
            top_class = int(torch.sigmoid(model(input_tensor)).argmax(dim=1).item())

        with GradCAM(model=model, target_layers=[layer]) as cam:
            grayscale_cam = cam(input_tensor=input_tensor, targets=[ClassifierOutputTarget(top_class)])[0]

        rgb_image = np.array(original.resize(grayscale_cam.shape[::-1])).astype(np.float32) / 255.0
        overlay = show_cam_on_image(rgb_image, grayscale_cam, use_rgb=True)

        destination = f"gradcam/{Path(image_path).stem}_heatmap.png"
        path = self.storage_service.base_dir / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(overlay).save(path)
        return str(path)
