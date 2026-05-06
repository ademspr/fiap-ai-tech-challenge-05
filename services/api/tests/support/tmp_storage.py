import hashlib
from pathlib import Path
from uuid import UUID

from hackathon_api.infrastructure.storage.local_files import diagram_relative_path


class TmpFilesystemStorage:
    """Test double for FileStoragePort using a temp directory (no MinIO)."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self.uploads_root = root / "uploads"
        self.reports_root = root / "reports"
        self.uploads_root.mkdir(parents=True, exist_ok=True)
        self.reports_root.mkdir(parents=True, exist_ok=True)

    def save_uploaded_diagram(
        self, job_id: UUID, filename: str, data: bytes
    ) -> tuple[str, str]:
        rel = diagram_relative_path(job_id, filename)
        dest = self.uploads_root.joinpath(*rel.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return rel, hashlib.sha256(data).hexdigest()

    def read_report_bytes(self, report_relative_path: str) -> bytes:
        return (self.reports_root / report_relative_path).read_bytes()
