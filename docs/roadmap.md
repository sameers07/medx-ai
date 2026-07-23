# Roadmap (2-Day Build)

Skeleton phase is complete (`v0.1.0` on `main`). Remaining work must ship in 2 days — the items
below are the compressed, must-have scope; anything marked *(stretch)* is cut first if time runs
short.

## Done
- [x] Repo scaffold, configs, DB models, API stubs, service stubs, Docker, tests (`v0.1.0` on `main`)

## Day 1 — Data + Model + Explainability (`feature/model-training`, `feature/gradcam`)
- [x] Dataset loader: `datasets/chest_xray_dataset.py` — `ChestXrayDataset` (real data, CSV +
      image dir, NIH ChestX-ray14/CheXpert-style labels) and `DummyChestXrayDataset` (random
      data, since no real dataset is downloaded yet — see `datasets/README.md`). Swap in real
      data by pointing `training/train.py` at `--labels-csv`/`--image-dir`.
- [x] Preprocessing: `app/preprocessing/transforms.py` — normalization (ImageNet stats),
      augmentation (train), resize-only (eval), sized from `config.yaml`. Train/val split in
      `training/train.py` (80/20).
- [x] Baseline model: `app/models/resnet.py` — ResNet-50, transfer learning from ImageNet, per
      `app/config/config.yaml` (`model.architecture: resnet50`, 14 classes, 224px input). No time
      for architecture comparisons (DenseNet/Swin) — ResNet-50 is final unless it clearly fails.
- [x] Metrics: per-label + averaged AUC computed in `training/train.py:evaluate()`. Target AUC ≥
      0.90 on held-out set — not yet measured against a real dataset (only exercised against
      dummy/random data so far).
- [x] Wire trained weights into `PredictionService` (`app/services/prediction_service.py`) —
      loads a checkpoint and returns `{class_name: probability}`.
- [x] Grad-CAM in `GradCAMService` (`app/services/gradcam_service.py`), targeting `layer4` per
      `config.yaml`, via `pytorch_grad_cam`. Tested that it produces a saved overlay of the right
      size — visual/clinical plausibility check still pending real data *(stretch, deferred)*.
- [x] `GradCAMService.generate_heatmap()` returns the saved path; wiring it onto
      `Prediction.gradcam_path` happens in Day 2's pipeline integration.

**Caveat:** all of the above is validated against `DummyChestXrayDataset` (random tensors), not
real chest X-rays — no dataset is downloaded in this repo yet. The code paths (loader → transform
→ model → Grad-CAM → checkpoint) work end-to-end; actual diagnostic accuracy is unmeasured until
real data is loaded via `--labels-csv`/`--image-dir`.

## Day 2 — Reports + API/UI + Ship (`feature/report-llm`, `feature/api-integration`, `feature/frontend`)
- [ ] `ReportService.generate_report()` (`app/services/report_service.py`): findings → prompt →
      narrative report via configured LLM (`report_generation` block in `config.yaml`, default
      OpenAI `gpt-4o-mini`). Manual spot-check of output quality; skip BLEU/ROUGE scoring
      *(stretch)*.
- [ ] Wire `ImageService` → `PredictionService` → `GradCAMService` → `ReportService` → DB persist
      into `run_pipeline()` (`app/inference/pipeline.py`) and the `/predict` route.
- [ ] `/history/{patient_id}` DB queries (`app/api/routes/history.py`).
- [ ] Streamlit frontend (`frontend/`): upload, prediction + Grad-CAM overlay, report, history view.
- [ ] Dockerize end-to-end, finalize README, tag `v1.0.0` on `main`.
- [ ] Auth (JWT/OAuth2 on patient-data endpoints) and per-inference audit logging *(stretch — only
      if Day 2 core items land early)*.

## Branch Flow
```
main --(v0.1.0)--> develop --> feature/* --> develop --> main (v1.0.0)
```
