"""Image preprocessing / augmentation pipelines, sized per app/config/config.yaml."""
from torchvision import transforms

from app.config.model_config import config

_INPUT_SIZE = config["model"]["input_size"]

# ImageNet stats — matches the pretrained ResNet-50 backbone's expected input distribution.
_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]


def get_transforms(train: bool) -> transforms.Compose:
    """Training pipeline augments; eval/inference pipeline only resizes + normalizes."""
    if train:
        return transforms.Compose(
            [
                transforms.RandomResizedCrop(_INPUT_SIZE, scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                transforms.Normalize(mean=_MEAN, std=_STD),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((_INPUT_SIZE, _INPUT_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=_MEAN, std=_STD),
        ]
    )
