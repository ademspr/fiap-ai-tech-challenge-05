from hackathon_platform.minio_io import get_object_bytes, put_object_bytes
from hackathon_platform.object_keys import reports_key, uploads_key

from hackathon_worker.config import settings
from hackathon_worker.infrastructure.storage.minio_client import minio_client_singleton


def read_diagram_bytes(relative_path: str) -> bytes:
    return get_object_bytes(
        minio_client_singleton(),
        settings.minio_bucket,
        uploads_key(relative_path),
    )


def write_report_bytes(relative_path: str, data: bytes) -> None:
    put_object_bytes(
        minio_client_singleton(),
        settings.minio_bucket,
        reports_key(relative_path),
        data,
    )
