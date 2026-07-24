# scripts

## download_sample_data.py

Downloads a small real subset of NIH ChestX-ray14 into `datasets/chestxray14/` — genuine chest
X-rays + genuine multi-label annotations, via the public (no account/API key needed) Hugging Face
mirror `Sohaibsoussi/NIH-Chest-X-ray-dataset-small`. Pulls individual images through the HF
datasets-server "rows" API rather than downloading the mirror's full parquet files.

```bash
python -m scripts.download_sample_data --n 300 --split train --out-dir datasets/chestxray14
python -m training.train --labels-csv datasets/chestxray14/labels.csv --image-dir datasets/chestxray14
```

Not wired into any test — it hits the network and its output is gitignored data, not code.
