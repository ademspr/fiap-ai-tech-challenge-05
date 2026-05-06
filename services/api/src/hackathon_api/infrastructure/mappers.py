from hackathon_api.domain.entities import AnalysisJob, Client
from hackathon_api.infrastructure.db.models import AnalysisJobModel, ClientModel


def client_from_model(model: ClientModel) -> Client:
    return Client(id=model.id, token_balance=int(model.token_balance))


def analysis_job_from_model(model: AnalysisJobModel) -> AnalysisJob:
    return AnalysisJob(
        id=model.id,
        client_id=model.client_id,
        status=model.status,
        diagram_storage_path=model.diagram_storage_path,
        report_storage_path=model.report_storage_path,
        report_schema_version=model.report_schema_version,
        content_type=model.content_type,
        size_bytes=int(model.size_bytes),
        diagram_checksum=model.diagram_checksum,
        report_checksum=model.report_checksum,
        tokens_used=int(model.tokens_used),
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
