class MissingMetadataKeys(Exception):
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        super().__init__(f"Missing required metadata keys: {keys}")
