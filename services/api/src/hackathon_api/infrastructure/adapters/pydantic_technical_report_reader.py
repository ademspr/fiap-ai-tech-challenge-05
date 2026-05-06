from typing import Any

from hackathon_contracts import TechnicalReportV1

from hackathon_api.application.ports import FileStoragePort, TechnicalReportReaderPort


class PydanticTechnicalReportReader(TechnicalReportReaderPort):
    """Reads report bytes and validates against the technical report contract."""

    def __init__(self, file_storage: FileStoragePort) -> None:
        self._files = file_storage

    def read_public_json(self, report_relative_path: str) -> dict[str, Any]:
        raw = self._files.read_report_bytes(report_relative_path)
        return TechnicalReportV1.model_validate_json(raw).model_dump(mode="json")
