"""
Baseline ResNet-50 training loop for multi-label chest X-ray classification.

Defaults to DummyChestXrayDataset (random data) so the pipeline can be exercised without a real
dataset. Pass --labels-csv/--image-dir to train on real data (see datasets/chest_xray_dataset.py).
"""
import argparse
from pathlib import Path

import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, random_split

from app.config.logging import get_logger, setup_logging
from app.config.model_config import config
from app.config.settings import settings
from app.models.resnet import build_model
from app.preprocessing.transforms import get_transforms
from datasets.chest_xray_dataset import ChestXrayDataset, DummyChestXrayDataset

logger = get_logger(__name__)


def build_dataset(args):
    if args.labels_csv and args.image_dir:
        return ChestXrayDataset(args.labels_csv, args.image_dir, transform=None)
    logger.warning("No --labels-csv/--image-dir given — training on DummyChestXrayDataset.")
    return DummyChestXrayDataset(size=args.dummy_size, input_size=config["model"]["input_size"])


def evaluate(model, loader, device) -> float:
    """Averaged multi-label AUC. Falls back to NaN if a batch has a single-class column."""
    model.eval()
    all_logits, all_labels = [], []
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            all_logits.append(model(images).cpu())
            all_labels.append(labels)
    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels)
    probs = torch.sigmoid(logits).numpy()
    labels = labels.numpy()

    aucs = []
    for i in range(labels.shape[1]):
        if len(set(labels[:, i])) < 2:
            continue
        aucs.append(roc_auc_score(labels[:, i], probs[:, i]))
    return sum(aucs) / len(aucs) if aucs else float("nan")


def train(args):
    setup_logging()
    device = torch.device(settings.device)

    train_tf = get_transforms(train=True)
    eval_tf = get_transforms(train=False)

    dataset = build_dataset(args)
    val_size = max(1, int(0.2 * len(dataset)))
    train_ds, val_ds = random_split(dataset, [len(dataset) - val_size, val_size])
    train_ds.dataset.transform = train_tf
    val_ds.dataset.transform = eval_tf

    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"])

    model = build_model(config["model"]["num_classes"], pretrained=config["model"]["pretrained"])
    model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=config["training"]["learning_rate"])
    criterion = torch.nn.BCEWithLogitsLoss()

    epochs = args.epochs or config["training"]["epochs"]
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        train_loss = running_loss / len(train_ds)
        val_auc = evaluate(model, val_loader, device)
        logger.info(f"epoch {epoch + 1}/{epochs} | train_loss={train_loss:.4f} | val_auc={val_auc:.4f}")

    checkpoint_path = Path(settings.model_weights_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), checkpoint_path)
    logger.info(f"Saved checkpoint to {checkpoint_path}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-csv", type=str, default=None)
    parser.add_argument("--image-dir", type=str, default=None)
    parser.add_argument("--dummy-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=None, help="Overrides config.yaml if set")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
