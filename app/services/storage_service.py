"""StorageService — local filesystem storage for uploads and generated artifacts (heatmaps)."""
import shutil
from pathlib import Path

from app.config.settings import settings


class StorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.storage_dir)

    def save(self, file, destination: str) -> str:
        """Writes `file` (a file-like object, or raw bytes) to base_dir/destination.

        Returns the path written to.
        """
        path = self.base_dir / destination
        path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file, (bytes, bytearray)):
            path.write_bytes(file)
        else:
            stream = getattr(file, "file", file)
            stream.seek(0)
            with open(path, "wb") as out:
                shutil.copyfileobj(stream, out)

        return str(path)

    def load(self, path: str) -> bytes:
        return (self.base_dir / path).read_bytes()
