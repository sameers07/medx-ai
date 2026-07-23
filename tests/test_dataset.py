from app.config.model_config import config
from datasets.chest_xray_dataset import CLASS_NAMES, DummyChestXrayDataset
from app.preprocessing.transforms import get_transforms


def test_dummy_dataset_shapes():
    dataset = DummyChestXrayDataset(size=4, input_size=config["model"]["input_size"], transform=get_transforms(train=False))
    assert len(dataset) == 4

    image, labels = dataset[0]
    assert image.shape == (3, config["model"]["input_size"], config["model"]["input_size"])
    assert labels.shape == (len(CLASS_NAMES),)
    assert set(labels.tolist()) <= {0.0, 1.0}


def test_dummy_dataset_is_deterministic_per_index():
    dataset = DummyChestXrayDataset(size=4, input_size=config["model"]["input_size"])
    image_a, labels_a = dataset[0]
    image_b, labels_b = dataset[0]
    assert (labels_a == labels_b).all()
