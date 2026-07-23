"""ImageService — validation for uploaded chest X-ray images.

Preprocessing (resize/normalize/tensor conversion) lands in feature/preprocessing.
"""
from PIL import Image, UnidentifiedImageError

_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class InvalidImageError(ValueError):
    pass


class ImageService:
    def validate(self, file) -> None:
        """Checks extension and that the content is a readable image.

        `file` is a FastAPI `UploadFile` (or anything exposing `.filename` and `.file`).
        Raises `InvalidImageError` on failure; returns None on success.
        """
        filename = getattr(file, "filename", "") or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in _ALLOWED_EXTENSIONS:
            raise InvalidImageError(f"Unsupported file extension: {filename!r}")

        stream = getattr(file, "file", file)
        try:
            image = Image.open(stream)
            image.verify()
        except UnidentifiedImageError as e:
            raise InvalidImageError(f"File is not a valid image: {filename!r}") from e
        finally:
            stream.seek(0)

    def preprocess(self, image_path: str):
        raise NotImplementedError("Wired up in feature/preprocessing")
