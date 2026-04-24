import hashlib
from pathlib import Path
from uuid import UUID

from hackathon_api.config import settings


def diagram_dir(job_id: UUID) -> Path:
    return settings.uploads_dir / str(job_id)


def save_uploaded_diagram(job_id: UUID, filename: str, data: bytes) -> tuple[str, str]:
    """Returns (relative_path_from_uploads_root, sha256_hex)."""
    dest_dir = diagram_dir(job_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    destination = dest_dir / safe_name
    destination.write_bytes(data)
    relative_path = f"{job_id}/{safe_name}"
    digest = hashlib.sha256(data).hexdigest()
    return relative_path, digest


def relative_report_path(job_id: UUID) -> str:
    return f"{job_id}.json"
