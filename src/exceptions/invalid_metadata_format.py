class InvalidMetadataFormat(Exception):
    def __init__(self) -> None:
        self.detail = "Invalid metadata format"
