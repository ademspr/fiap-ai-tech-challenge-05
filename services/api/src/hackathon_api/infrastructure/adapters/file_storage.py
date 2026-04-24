from hackathon_api.config import settings
from hackathon_api.infrastructure.storage import local_files


class LocalFileStorageAdapter:
    def save_uploaded_diagram(self, job_id, filename: str, data: bytes) -> tuple[str, str]:
        return local_files.save_uploaded_diagram(job_id, filename, data)

    def read_report_bytes(self, report_relative_path: str) -> bytes:
        return (settings.reports_dir / report_relative_path).read_bytes()
