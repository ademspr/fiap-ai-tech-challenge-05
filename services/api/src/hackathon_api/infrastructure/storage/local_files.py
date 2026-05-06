import hashlib
from pathlib import Path
from uuid import UUID


def diagram_relative_path(job_id: UUID, filename: str) -> str:
    safe_name = Path(filename).name
    return f"{job_id}/{safe_name}"


def relative_report_path(job_id: UUID) -> str:
    return f"{job_id}.json"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
