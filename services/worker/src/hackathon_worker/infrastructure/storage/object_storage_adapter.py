from hackathon_worker.application.ports import WorkerObjectStoragePort
from hackathon_worker.infrastructure.storage import blob_store


class MinioObjectStorageAdapter(WorkerObjectStoragePort):
    def read_diagram_bytes(self, relative_path: str) -> bytes:
        return blob_store.read_diagram_bytes(relative_path)

    def write_report_bytes(self, relative_path: str, data: bytes) -> None:
        blob_store.write_report_bytes(relative_path, data)
