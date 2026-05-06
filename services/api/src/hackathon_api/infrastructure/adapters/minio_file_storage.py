import hashlib
from uuid import UUID

from hackathon_platform.minio_io import get_object_bytes, put_object_bytes
from hackathon_platform.object_keys import reports_key, uploads_key
from minio import Minio

from hackathon_api.application.ports import FileStoragePort
from hackathon_api.infrastructure.storage import local_files


class MinioFileStorageAdapter(FileStoragePort):
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def save_uploaded_diagram(
        self, job_id: UUID, filename: str, data: bytes
    ) -> tuple[str, str]:
        relative_path = local_files.diagram_relative_path(job_id, filename)
        digest = hashlib.sha256(data).hexdigest()
        put_object_bytes(self._client, self._bucket, uploads_key(relative_path), data)
        return relative_path, digest

    def read_report_bytes(self, report_relative_path: str) -> bytes:
        return get_object_bytes(self._client, self._bucket, reports_key(report_relative_path))
