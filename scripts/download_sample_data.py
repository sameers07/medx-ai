"""
Downloads a small real subset of NIH ChestX-ray14 (via the public, no-auth-required Hugging Face
mirror `Sohaibsoussi/NIH-Chest-X-ray-dataset-small`) into datasets/chestxray14/, so
training/train.py can be pointed at genuine chest X-rays instead of DummyChestXrayDataset.

Uses the HF datasets-server "rows" API to pull individual images without downloading the
mirror's full parquet files (each hundreds of MB).

Resumable: if labels.csv already has N rows, a rerun with the same --split picks up at row N
instead of re-downloading from scratch — a transient network failure partway through a large
--n doesn't waste the images already saved.
"""
import argparse
import csv
import time
from pathlib import Path

import requests

from app.config.model_config import config

HF_DATASET = "Sohaibsoussi/NIH-Chest-X-ray-dataset-small"
ROWS_API = "https://datasets-server.huggingface.co/rows"
PAGE_SIZE = 100
MAX_RETRIES = 5
TIMEOUT = 60

CLASS_NAMES: list[str] = config["model"]["class_names"]
# Row 0 in the HF label schema is "No Finding" — not one of our 14 disease columns, so a row
# whose only label is "No Finding" correctly becomes an all-zero vector across CLASS_NAMES.
HF_LABEL_NAMES = ["No Finding"] + CLASS_NAMES


def _get_with_retry(url: str, **kwargs) -> requests.Response:
    """A flaky network hiccup shouldn't kill a multi-hundred-image download run."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2**attempt)


def fetch_rows(split: str, offset: int, length: int) -> list[dict]:
    resp = _get_with_retry(
        ROWS_API,
        params={"dataset": HF_DATASET, "config": "default", "split": split, "offset": offset, "length": length},
    )
    return resp.json()["rows"]


def _already_downloaded(labels_csv: Path) -> int:
    """Returns how many valid rows are already saved, discarding a trailing malformed row.

    A crash mid-write (rare, since each row is flushed immediately, but not impossible) could
    leave a torn final line. Trusting that line's column count would either miscount the resume
    point or leave a corrupt row sitting in the middle of the file once new rows get appended
    after it — so it's truncated here before anything resumes.
    """
    if not labels_csv.exists():
        return 0
    with open(labels_csv, newline="") as f:
        lines = f.readlines()
    if not lines:
        return 0

    header, rows = lines[0], lines[1:]
    expected_cols = len(header.strip().split(","))
    valid_rows = [line for line in rows if len(line.strip().split(",")) == expected_cols]
    # Only trust a *trailing* malformed row as "interrupted mid-write" — a malformed row
    # anywhere else would indicate a different problem worth failing loudly on instead.
    if len(valid_rows) != len(rows) and valid_rows == rows[: len(valid_rows)]:
        with open(labels_csv, "w", newline="") as f:
            f.writelines([header, *valid_rows])
    return len(valid_rows)


def download(n: int, split: str, out_dir: Path) -> None:
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    labels_csv = out_dir / "labels.csv"

    start = _already_downloaded(labels_csv)
    if start >= n:
        print(f"Already have {start} >= {n} rows in {labels_csv}, nothing to do.")
        return
    if start:
        print(f"Resuming: {start} rows already in {labels_csv}, continuing from there.")

    mode = "a" if start else "w"
    with open(labels_csv, mode, newline="") as f:
        writer = csv.writer(f)
        if not start:
            writer.writerow(["image_path", *CLASS_NAMES])

        rows_written = start
        offset = start
        while rows_written < n:
            batch = fetch_rows(split, offset, min(PAGE_SIZE, n - rows_written))
            if not batch:
                break
            for item in batch:
                row = item["row"]
                image_url = row["image"]["src"]
                label_indices = set(row["labels"])

                filename = f"{split}_{item['row_idx']}.jpg"
                image_bytes = _get_with_retry(image_url).content
                (image_dir / filename).write_bytes(image_bytes)

                one_hot = [1 if HF_LABEL_NAMES.index(name) in label_indices else 0 for name in CLASS_NAMES]
                writer.writerow([f"images/{filename}", *one_hot])
                f.flush()
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
