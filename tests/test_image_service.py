from PIL import Image

from app.config.model_config import config
from app.services.image_service import ImageService

_INPUT_SIZE = config["model"]["input_size"]


def test_preprocess_returns_batched_normalized_tensor(tmp_path):
    image_path = tmp_path / "xray.png"
    Image.new("RGB", (300, 200), color=(90, 90, 90)).save(image_path)

    tensor = ImageService().preprocess(str(image_path))

    assert tensor.shape == (1, 3, _INPUT_SIZE, _INPUT_SIZE)


def test_preprocess_converts_grayscale_to_rgb(tmp_path):
    image_path = tmp_path / "xray_gray.png"
    Image.new("L", (300, 200), color=90).save(image_path)

    tensor = ImageService().preprocess(str(image_path))

    assert tensor.shape == (1, 3, _INPUT_SIZE, _INPUT_SIZE)
