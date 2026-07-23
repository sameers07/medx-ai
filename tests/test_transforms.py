from PIL import Image

from app.config.model_config import config
from app.preprocessing.transforms import get_transforms

_INPUT_SIZE = config["model"]["input_size"]


def _dummy_image():
    return Image.new("RGB", (300, 200), color=(128, 64, 32))


def test_eval_transform_shape():
    tensor = get_transforms(train=False)(_dummy_image())
    assert tensor.shape == (3, _INPUT_SIZE, _INPUT_SIZE)


def test_train_transform_shape():
    tensor = get_transforms(train=True)(_dummy_image())
    assert tensor.shape == (3, _INPUT_SIZE, _INPUT_SIZE)
