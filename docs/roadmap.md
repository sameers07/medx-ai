# Roadmap (2-Day Build)

## Day 1 — Skeleton + Core Pipeline
- [x] Repo scaffold, configs, DB models, API stubs, service stubs, Docker, tests (`v0.1.0` on `main`)
- [ ] `develop` branch: real dataset loader + baseline ResNet-50 training (`feature/model-training`)
- [ ] Grad-CAM integration (`feature/gradcam`)

## Day 2 — Reports + API/UI + Ship
- [ ] LLM report generation wired to model output (`feature/report-llm`)
- [ ] Wire prediction + gradcam + report into `/predict`, add `/history` DB queries (`feature/api-integration`)
- [ ] Streamlit frontend (`feature/frontend`)
- [ ] Dockerize, finalize README, tag `v1.0.0` on `main`

## Branch Flow
```
main --(v0.1.0)--> develop --> feature/* --> develop --> main (v1.0.0)
```
