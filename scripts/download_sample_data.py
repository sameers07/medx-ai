"""
Downloads a small real subset of NIH ChestX-ray14 (via the public, no-auth-required Hugging Face
mirror `Sohaibsoussi/NIH-Chest-X-ray-dataset-small`) into datasets/chestxray14/, so
training/train.py can be pointed at genuine chest X-rays instead of DummyChestXrayDataset.

Uses the HF datasets-server "rows" API to pull individual images without downloading the
mirror's full parquet files (each hundreds of MB).
"""
import argparse
import csv
from pathlib import Path

import requests

from app.config.model_config import config

HF_DATASET = "Sohaibsoussi/NIH-Chest-X-ray-dataset-small"
ROWS_API = "https://datasets-server.huggingface.co/rows"
PAGE_SIZE = 100

CLASS_NAMES: list[str] = config["model"]["class_names"]
# Row 0 in the HF label schema is "No Finding" — not one of our 14 disease columns, so a row
# whose only label is "No Finding" correctly becomes an all-zero vector across CLASS_NAMES.
HF_LABEL_NAMES = ["No Finding"] + CLASS_NAMES


def fetch_rows(split: str, offset: int, length: int) -> list[dict]:
    resp = requests.get(
        ROWS_API,
        params={"dataset": HF_DATASET, "config": "default", "split": split, "offset": offset, "length": length},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["rows"]


def download(n: int, split: str, out_dir: Path) -> None:
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    labels_csv = out_dir / "labels.csv"

    rows_written = 0
    with open(labels_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", *CLASS_NAMES])

        offset = 0
        while rows_written < n:
            batch = fetch_rows(split, offset, min(PAGE_SIZE, n - rows_written))
            if not batch:
                break
            for item in batch:
                row = item["row"]
                image_url = row["image"]["src"]
                label_indices = set(row["labels"])

                filename = f"{split}_{offset + item['row_idx']}.jpg"
                image_bytes = requests.get(image_url, timeout=30).content
                (image_dir / filename).write_bytes(image_bytes)

                one_hot = [1 if HF_LABEL_NAMES.index(name) in label_indices else 0 for name in CLASS_NAMES]
                writer.writerow([f"images/{filename}", *one_hot])
                rows_written += 1

            offset += len(batch)
            print(f"Downloaded {rows_written}/{n}")

    print(f"Saved {rows_written} images + labels to {out_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=300, help="Number of images to download")
    parser.add_argument("--split", type=str, default="train", choices=["train", "test"])
    parser.add_argument("--out-dir", type=str, default="datasets/chestxray14")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download(args.n, args.split, Path(args.out_dir))
