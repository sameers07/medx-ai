import torch

from app.models.resnet import build_model


def test_build_model_output_shape():
    model = build_model(num_classes=14, pretrained=False)
    model.eval()
    with torch.no_grad():
        logits = model(torch.randn(2, 3, 224, 224))
    assert logits.shape == (2, 14)
