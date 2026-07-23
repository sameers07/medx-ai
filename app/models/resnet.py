"""ResNet-50 baseline for multi-label chest X-ray classification."""
import torch.nn as nn
from torchvision.models import resnet50, ResNet50_Weights


def build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    """Builds a ResNet-50 with its final layer replaced for multi-label classification.

    Outputs raw logits (one per class) — pair with BCEWithLogitsLoss for training and
    a sigmoid for inference, since a chest X-ray can show multiple conditions at once.
    """
    weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
    model = resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model
