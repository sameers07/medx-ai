# Model

```
Dataset -> Preprocessing -> Training -> Validation -> Checkpoint -> Inference
```

## Dataset

`datasets/chest_xray_dataset.py` provides two implementations behind the same interface
(`torch.utils.data.Dataset`):
- **`ChestXrayDataset`** — real data: a labels CSV (`image_path` + one 0/1 column per
  `config.yaml`'s `model.class_names`) + an image directory. `scripts/download_sample_data.py`
  builds exactly this format from a small (~300 image) real NIH ChestX-ray14 subset, pulled from a
  public, no-auth-required Hugging Face mirror.
- **`DummyChestXrayDataset`** — random tensors + random multi-hot labels, no download or network
  needed. Used for fast pipeline smoke-testing (this is what the test suite uses), not for
  producing a usable model.

`training/train.py` does an 80/20 train/val split via `torch.utils.data.random_split` — no
stratification by label, which matters at small sample sizes (see
[known-limitations.md](known-limitations.md)).

## Preprocessing (`app/preprocessing/transforms.py`)

RGB conversion → resize (`config.yaml`'s `model.input_size`, 224) → tensor → ImageNet
normalization (`mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]` — matches the pretrained
backbone's expected input distribution). Training adds `RandomResizedCrop` + `RandomHorizontalFlip`
as augmentation; eval/inference only resizes (no augmentation) — see `get_transforms(train: bool)`.

## Training (`training/train.py`)

- **Transfer learning:** ResNet-50 pretrained on ImageNet (`app/models/resnet.py:build_model()`),
  final `fc` layer replaced with a `Linear` to `num_classes` (14). Multi-label, not multi-class —
  every class gets an independent sigmoid, not a shared softmax.
- **Loss:** `BCEWithLogitsLoss` — the standard choice for multi-label classification (each of the
  14 labels is an independent binary decision; a single chest X-ray can and often does show
  multiple findings at once).
- **Optimizer:** Adam, learning rate from `config.yaml`'s `training.learning_rate` (`0.0001`).
- **Scheduler:** none. This is a real gap, not a considered omission — a constant learning rate is
  fine for a handful of epochs on a small dataset, but would need a decay schedule (e.g. cosine or
  step) to train well at real scale.
- **Batch size / epochs:** from `config.yaml`'s `training` block (`batch_size: 32`, `epochs: 20`),
  overridable via `--epochs` on the CLI.

```bash
python -m scripts.download_sample_data --n 300 --split train
python -m training.train --labels-csv datasets/chestxray14/labels.csv --image-dir datasets/chestxray14 --epochs 3
```

## Validation

`evaluate()` in `training/train.py` computes **per-label AUC** (`sklearn.roc_auc_score`) on the
held-out validation split, then averages across labels that have both classes present (a label
with zero positive examples in a small validation split is skipped, not scored as 0 or 1). Logged
every epoch alongside training loss.

A real run against the 300-image real subset (see `docs/roadmap.md`'s `feature/real-data` entry):
val AUC climbed **0.57 → 0.70** over 3 epochs — real learning, on real data, far from the
documented target.

## Checkpoint

Saved as a plain `state_dict()` to `settings.model_weights_path` (`training/checkpoints/model.pth`
by default) — no optimizer state, no epoch counter, so training can't be resumed mid-run today
(another real gap).

## Inference (`app/services/prediction_service.py`)

`PredictionService` loads the checkpoint once (`torch.load(..., weights_only=True)` — not the
default, deliberately: avoids executing arbitrary pickled code from an untrusted checkpoint file),
builds the same `build_model()` architecture, and is lazily instantiated + cached
(`@lru_cache(maxsize=1)` in `app/api/routes/predict.py`) so the app boots fine with no trained
checkpoint at all — `/predict` returns `503` instead of crashing on startup or on first request.

## Evaluation target vs. reality

`config.yaml`/`docs/roadmap.md` document an aspirational target of **AUC ≥ 0.90** on a held-out
set, matching published ResNet-50 baselines on the full ChestX-ray14 dataset (~112k images). The
300-image run above proves the pipeline learns, not that the target is met — see
[known-limitations.md](known-limitations.md) for the honest gap between the two.
