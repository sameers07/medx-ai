"""ImageService — stub. Image validation/preprocessing not wired in yet."""


class ImageService:
    def validate(self, file):
        raise NotImplementedError

    def preprocess(self, image_path: str):
        raise NotImplementedError
