"""
Baseline ResNet-50 training loop for multi-label chest X-ray classification.

Defaults to DummyChestXrayDataset (random data) so the pipeline can be exercised without a real
dataset. Pass --labels-csv/--image-dir to train on real data (see datasets/chest_xray_dataset.py).
"""
import argparse
from pathlib import Path

import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Subset

from app.config.logging import get_logger, setup_logging
from app.config.model_config import config
from app.config.settings import settings
from app.models.resnet import build_model
from app.preprocessing.transforms import get_transforms
from datasets.chest_xray_dataset import ChestXrayDataset, DummyChestXrayDataset

logger = get_logger(__name__)


def build_dataset(args, transform=None):
    if args.labels_csv and args.image_dir:
        return ChestXrayDataset(args.labels_csv, args.image_dir, transform=transform)
    return DummyChestXrayDataset(
        size=args.dummy_size, input_size=config["model"]["input_size"], transform=transform
    )


def compute_pos_weight(loader) -> torch.Tensor:
    """neg/pos ratio per class, for BCEWithLogitsLoss's pos_weight (class-imbalance correction).

    Capped at 50x — an uncapped ratio on a near-zero-positive class (e.g. Hernia at this dataset
    size) would massively over-weight the rare positive examples and destabilize training.
    """
    all_labels = torch.cat([labels for _, labels in loader])
    pos = all_labels.sum(dim=0)
    neg = all_labels.shape[0] - pos
    return (neg / pos.clamp(min=1)).clamp(max=50.0)


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
    # Fixed seed for reproducibility — without this, weight init, the train/val split, and
    # shuffling all vary between runs, so identical hyperparameters can yield different results
    # (hit this for real: two runs of the same config produced val AUC 0.71 vs 0.66).
    torch.manual_seed(args.seed)
    device = torch.device(settings.device)

    if not (args.labels_csv and args.image_dir):
        logger.warning("No --labels-csv/--image-dir given — training on DummyChestXrayDataset.")

    train_tf = get_transforms(train=True)
    eval_tf = get_transforms(train=False)

    # Build two separate dataset instances (one per transform) rather than splitting one
    # dataset with random_split and mutating .transform afterwards — Subset.dataset is a
    # shared reference, so setting it for val after train silently left *both* splits using
    # eval_tf (no augmentation was ever actually applied during training).
    n = len(build_dataset(args))
    val_size = max(1, int(0.2 * n))
    generator = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(n, generator=generator).tolist()
    val_indices, train_indices = perm[:val_size], perm[val_size:]

    train_ds = Subset(build_dataset(args, transform=train_tf), train_indices)
    val_ds = Subset(build_dataset(args, transform=eval_tf), val_indices)

    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"])

    model = build_model(config["model"]["num_classes"], pretrained=config["model"]["pretrained"])
    model.to(device)

    epochs = args.epochs or config["training"]["epochs"]

    optimizer = torch.optim.Adam(model.parameters(), lr=config["training"]["learning_rate"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    pos_weight = compute_pos_weight(train_loader).to(device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    checkpoint_path = Path(settings.model_weights_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    best_val_auc = float("-inf")

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
        lr = scheduler.get_last_lr()[0]
        scheduler.step()

        # Save whenever val AUC improves, not just at the end — without this, a model that
        # overfits in later epochs (train_loss keeps dropping, val_auc gets worse) silently
        # ships the worse, overfit checkpoint. NaN comparisons are always False, so a NaN
        # val_auc (e.g. a validation split with a single-class column) never overwrites.
        is_best = val_auc > best_val_auc
        if is_best:
            best_val_auc = val_auc
            torch.save(model.state_dict(), checkpoint_path)

        logger.info(
            f"epoch {epoch + 1}/{epochs} | train_loss={train_loss:.4f} | val_auc={val_auc:.4f} "
            f"| lr={lr:.6f}" + (" | new best, saved" if is_best else "")
        )

    if best_val_auc == float("-inf"):
        # val_auc was NaN every epoch (e.g. a validation split too small to compute AUC at all) —
        # still need *a* checkpoint rather than none, so fall back to the final epoch's weights.
        logger.warning("val_auc was never computable; saving final epoch's weights instead of 'best'.")
        torch.save(model.state_dict(), checkpoint_path)

    logger.info(f"Training complete. Best val_auc={best_val_auc:.4f}, checkpoint at {checkpoint_path}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-csv", type=str, default=None)
    parser.add_argument("--image-dir", type=str, default=None)
    parser.add_argument("--dummy-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=None, help="Overrides config.yaml if set")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
