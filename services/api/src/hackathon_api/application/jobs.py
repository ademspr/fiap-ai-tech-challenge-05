from typing import Any
from uuid import UUID

from hackathon_api.application.persistence import UnitOfWork
from hackathon_api.application.ports import (
    AnalyzeJobPublisherPort,
    ClientAuthenticatorPort,
    FileStoragePort,
    TechnicalReportReaderPort,
)
from hackathon_api.domain.entities import AnalysisJob, Client
from hackathon_api.domain.policies import ALLOWED_CONTENT_TYPES, UploadPolicy

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "UploadPolicy",
    "authenticate_client",
    "create_analysis_job",
    "get_job_by_id",
    "get_job_for_client",
    "load_report_for_api",
    "internal_apply_job_patch",
    "internal_complete_job",
]


async def authenticate_client(
    bearer_plain: str, *, authenticator: ClientAuthenticatorPort
) -> Client | None:
    return await authenticator.authenticate_bearer(bearer_plain)


async def create_analysis_job(
    job_persistence: UnitOfWork,
    client: Client,
    *,
    file_storage: FileStoragePort,
    analyze_publisher: AnalyzeJobPublisherPort,
    policy: UploadPolicy,
    filename: str,
    content_type: str,
    data: bytes,
) -> AnalysisJob:
    policy.validate_new_upload(content_type, len(data))
    client.require_minimum_balance_for_upload(policy.min_tokens_estimate)

    job = await job_persistence.jobs.create_received(
        client_id=client.id,
        content_type=content_type,
        size_bytes=len(data),
    )

    relative_path, digest = file_storage.save_uploaded_diagram(job.id, filename, data)
    await job_persistence.jobs.set_diagram(job.id, relative_path, digest)
    await job_persistence.commit()

    job = await job_persistence.jobs.get_by_id(job.id)
    assert job is not None
    await analyze_publisher.publish(job.id, relative_path)
    return job


async def get_job_by_id(job_persistence: UnitOfWork, job_id: UUID) -> AnalysisJob | None:
    return await job_persistence.jobs.get_by_id(job_id)


async def get_job_for_client(
    job_persistence: UnitOfWork,
    client_id: UUID,
    job_id: UUID,
) -> AnalysisJob:
    return await job_persistence.jobs.get_for_client(client_id, job_id)


def load_report_for_api(
    job: AnalysisJob,
    *,
    report_reader: TechnicalReportReaderPort,
) -> dict[str, Any]:
    if not job.report_storage_path:
        raise FileNotFoundError
    return report_reader.read_public_json(job.report_storage_path)


async def internal_apply_job_patch(
    job_persistence: UnitOfWork,
    job_id: UUID,
    *,
    status: str,
    error_message: str | None,
) -> None:
    await job_persistence.jobs.apply_status_patch(job_id, status, error_message)


async def internal_complete_job(
    job_persistence: UnitOfWork,
    job_id: UUID,
    *,
    report_storage_path: str,
    tokens_used: int,
    report_checksum: str | None,
    report_schema_version: int,
) -> None:
    await job_persistence.jobs.complete_with_report(
        job_id,
        report_storage_path=report_storage_path,
        tokens_used=tokens_used,
        report_checksum=report_checksum,
        report_schema_version=report_schema_version,
    )
