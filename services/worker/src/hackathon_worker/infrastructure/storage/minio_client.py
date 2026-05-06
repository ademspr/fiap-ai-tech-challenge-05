from minio import Minio

from hackathon_worker.config import settings


def build_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )


_singleton: Minio | None = None


def minio_client_singleton() -> Minio:
    global _singleton
    if _singleton is None:
        _singleton = build_minio_client()
    return _singleton
