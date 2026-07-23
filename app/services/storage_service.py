"""StorageService — stub. File/object storage handling not wired in yet."""


class StorageService:
    def save(self, file, destination: str):
        raise NotImplementedError

    def load(self, path: str):
        raise NotImplementedError
