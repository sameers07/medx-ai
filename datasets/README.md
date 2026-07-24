# datasets

Data itself is gitignored (`datasets/*`, except `README.md` and `*.py`) — only loader code and
this doc are tracked in git.

`chest_xray_dataset.py` — `ChestXrayDataset` (real data: labels CSV + image dir) and
`DummyChestXrayDataset` (random tensors, no download needed).

For a real, if small, dataset: `python -m scripts.download_sample_data` pulls a genuine NIH
ChestX-ray14 subset into `datasets/chestxray14/` (see `scripts/README.md`). For the full 112k-image
dataset, see the official NIH release: https://nihcc.app.box.com/v/ChestXray-NIHCC.
