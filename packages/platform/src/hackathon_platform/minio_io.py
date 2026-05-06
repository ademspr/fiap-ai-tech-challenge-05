from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from minio import Minio


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object_bytes(client: Minio, bucket: str, key: str, data: bytes) -> None:
    client.put_object(bucket, key, BytesIO(data), length=len(data))


def get_object_bytes(client: Minio, bucket: str, key: str) -> bytes:
    obj = client.get_object(bucket, key)
    try:
        return obj.read()
    finally:
        obj.close()
        obj.release_conn()
