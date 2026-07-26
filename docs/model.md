# Model

```
Dataset -> Preprocessing -> Training -> Validation -> Checkpoint -> Inference
```

## Dataset

`datasets/chest_xray_dataset.py` provides two implementations behind the same interface
(`torch.utils.data.Dataset`):
- **`ChestXrayDataset`** — real data: a labels CSV (`image_path` + one 0/1 column per
  `config.yaml`'s `model.class_names`) + an image directory. `scripts/download_sample_data.py`
  builds exactly this format from a small (~2,000 image) real NIH ChestX-ray14 subset, pulled from
  a public, no-auth-required Hugging Face mirror.
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
- **Loss:** `BCEWithLogitsLoss` with **per-class `pos_weight`** (`compute_pos_weight()`) — the
  neg/pos ratio for each of the 14 classes, capped at 50x. Without this, rare classes (e.g. Hernia,
  a handful of positives out of thousands of images) get almost no training signal; the cap
  prevents an extremely rare class from being over-corrected into instability.
- **Optimizer:** Adam, initial learning rate from `config.yaml`'s `training.learning_rate`
  (`0.0001`), decayed via `CosineAnnealingLR` over the run (`T_max=epochs`) — added after the
  first real training run showed a flat LR was a real limitation, not a hypothetical one.
- **Checkpoint selection:** the checkpoint saved to disk is the **best epoch by validation AUC**,
  not simply the last one — see "Overfitting, observed twice" below for why this matters in
  practice, not just in theory.
- **Batch size / epochs:** from `config.yaml`'s `training` block (`batch_size: 32`, `epochs: 20`),
  overridable via `--epochs` on the CLI.

```bash
python -m scripts.download_sample_data --n 2000 --split train
python -m training.train --labels-csv datasets/chestxray14/labels.csv --image-dir datasets/chestxray14 --epochs 10
```

`settings.device` (`DEVICE` in `.env`) defaults to `cpu`. On Apple Silicon, `DEVICE=mps` uses the
GPU via PyTorch's Metal backend — roughly 5x faster per epoch in practice on this project's
dataset size (~60-70s/epoch on MPS vs. ~5-6 min/epoch on CPU). No CUDA GPU is available in this
project's dev/CI environment, but `DEVICE=cuda` would work the same way if one were.

## Validation

`evaluate()` in `training/train.py` computes **per-label AUC** (`sklearn.roc_auc_score`) on the
held-out validation split, then averages across labels that have both classes present (a label
with zero positive examples in a small validation split is skipped, not scored as 0 or 1). Logged
every epoch alongside training loss and the current learning rate.

## Overfitting, observed repeatedly

A real training run on 2,000 real images for 10 epochs (`--seed 42`, for reproducibility — see
below): **val AUC peaked at 0.72 (epoch 3)**, while train loss kept dropping all the way to 0.14 by
epoch 10 — the model was fitting the training set increasingly well while validation performance
plateaued and drifted down for the rest of the run. This is not a one-off: three separate runs at
this scale (one on CPU, two on MPS, before and after fixing the random seed) all showed the same
shape — val AUC peaks early (epoch 3–5) then degrades while train loss keeps falling. That's a
real, reproducible characteristic of training at this dataset size, not noise.

**Reproducibility note:** the exact peak epoch/AUC vary between runs of identical hyperparameters
if no random seed is fixed (hit this directly — two otherwise-identical runs produced 0.71 and 0.66
before `training/train.py` set `torch.manual_seed()`). `--seed` (default 42) now makes weight
init, the train/val split, and data shuffling reproducible.

This is exactly why checkpoint selection now saves the best epoch, not the last: before that fix,
the *actual saved checkpoint* was the worse, overfit one, even though the training run itself
reached a better point partway through. A genuinely full fix (more data, stronger augmentation,
or explicit early stopping to cut training short rather than just discarding the worse epochs)
is future work — see [known-limitations.md](known-limitations.md).

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
2,000-image run above proves the pipeline learns, not that the target is met — see
[known-limitations.md](known-limitations.md) for the honest gap between the two.
