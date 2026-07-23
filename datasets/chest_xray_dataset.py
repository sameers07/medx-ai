"""
Chest X-ray dataset loaders for multi-label disease classification.

`ChestXrayDataset` expects a labels CSV (one row per study) with an image path column and one
0/1 column per class in `app/config/config.yaml`'s `model.class_names` — the layout used by
NIH ChestX-ray14 / CheXpert-style label files. Point it at a real dataset once one is available
(see datasets/README.md).

`DummyChestXrayDataset` generates random images/labels so the training loop, model, and Grad-CAM
code paths can be built and tested before real data is downloaded.
"""
import csv
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from app.config.model_config import config

CLASS_NAMES: list[str] = config["model"]["class_names"]


class ChestXrayDataset(Dataset):
    def __init__(self, labels_csv: str, image_dir: str, transform=None):
        self.image_dir = Path(image_dir)
        self.transform = transform
        with open(labels_csv, newline="") as f:
            self.rows = list(csv.DictReader(f))

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows[idx]
        image = Image.open(self.image_dir / row["image_path"]).convert("RGB")
        if self.transform:
            image = self.transform(image)
        labels = torch.tensor([float(row[name]) for name in CLASS_NAMES])
        return image, labels


class DummyChestXrayDataset(Dataset):
    """Random images + random multi-hot labels — no real data required."""

    def __init__(self, size: int = 64, input_size: int = 224, transform=None):
        self.size = size
        self.input_size = input_size
        self.transform = transform

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int):
        generator = torch.Generator().manual_seed(idx)
        image = Image.fromarray(
            (torch.rand(self.input_size, self.input_size, 3, generator=generator) * 255)
            .byte()
            .numpy()
        )
        if self.transform:
            image = self.transform(image)
        labels = torch.randint(0, 2, (len(CLASS_NAMES),), generator=generator).float()
        return image, labels
