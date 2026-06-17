class InspectionPhotoNotFound(Exception):
    def __init__(self, storage_key: str) -> None:
        self.storage_key = storage_key
        super().__init__(f"Inspection photo {storage_key} not found")
