from argparse import Namespace

from app.config import model_config
from app.config.settings import settings
from training.train import train


def test_train_smoke_runs_and_saves_checkpoint(tmp_path, monkeypatch):
    """End-to-end smoke test on DummyChestXrayDataset — no real data, no network required."""
    monkeypatch.setitem(model_config.config["model"], "pretrained", False)
    monkeypatch.setattr(settings, "model_weights_path", str(tmp_path / "model.pth"))

    args = Namespace(labels_csv=None, image_dir=None, dummy_size=8, epochs=1)
    train(args)

    assert (tmp_path / "model.pth").exists()
