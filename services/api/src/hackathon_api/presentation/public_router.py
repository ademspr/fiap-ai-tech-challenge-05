from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from hackathon_api.application.jobs import (
    create_analysis_job,
    get_job_for_client,
    load_report_for_api,
)
from hackathon_api.application.persistence import UnitOfWork
from hackathon_api.application.ports import (
    AnalyzeJobPublisherPort,
    FileStoragePort,
    JobMetricsPort,
    TechnicalReportReaderPort,
)
from hackathon_api.domain.entities import Client
from hackathon_api.domain.enums import JobStatus
from hackathon_api.domain.exceptions import (
    ForbiddenJobError,
    InsufficientTokensError,
    JobNotFoundError,
    JobServiceError,
    MessagingFailedError,
    PayloadTooLargeError,
    UnmappedJobServiceError,
    UnsupportedMediaTypeError,
)
from hackathon_api.domain.policies import UploadPolicy
from hackathon_api.presentation.deps import (
    get_analyze_job_publisher,
    get_current_client,
    get_file_storage,
    get_job_metrics,
    get_job_persistence,
    get_technical_report_reader,
    get_upload_policy,
)
from hackathon_api.presentation.schemas import (
    AnalysisJobCreateResponse,
    AnalysisJobPublicView,
    TokenBalanceResponse,
)

router = APIRouter(tags=["public"])


@router.post(
    "/analysis-jobs",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisJobCreateResponse,
    responses={201: {"headers": {"Location": {"schema": {"type": "string"}}}}},
)
async def post_analysis_job(
    request: Request,
    job_persistence: Annotated[UnitOfWork, Depends(get_job_persistence)],
    client: Annotated[Client, Depends(get_current_client)],
    file_storage: Annotated[FileStoragePort, Depends(get_file_storage)],
    analyze_publisher: Annotated[AnalyzeJobPublisherPort, Depends(get_analyze_job_publisher)],
    policy: Annotated[UploadPolicy, Depends(get_upload_policy)],
    job_metrics: Annotated[JobMetricsPort, Depends(get_job_metrics)],
    file: Annotated[UploadFile, File(...)],
):
    if not file.filename:
        raise HTTPException(400, "filename required")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        job = await create_analysis_job(
            job_persistence,
            client,
            file_storage=file_storage,
            analyze_publisher=analyze_publisher,
            policy=policy,
            filename=file.filename,
            content_type=content_type,
            data=data,
        )
    except JobServiceError as error:
        if isinstance(error, UnsupportedMediaTypeError):
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "Unsupported file type",
            )
        if isinstance(error, PayloadTooLargeError):
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "File too large",
            )
        if isinstance(error, InsufficientTokensError):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                "Insufficient token balance",
            )
        if isinstance(error, MessagingFailedError):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Queue unavailable",
            )
        raise UnmappedJobServiceError(
            f"Unhandled JobServiceError: {type(error).__name__}"
        ) from error

    job_metrics.increment_status_label(JobStatus.RECEIVED.value)
    job_metrics.add_upload_bytes(len(data))

    base = str(request.base_url).rstrip("/")
    location = f"{base}/v1/analysis-jobs/{job.id}"
    create_response = AnalysisJobCreateResponse(id=job.id, status=JobStatus(job.status))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=create_response.model_dump(mode="json"),
        headers={"Location": location},
    )


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobPublicView)
async def get_analysis_job(
    job_id: UUID,
    job_persistence: Annotated[UnitOfWork, Depends(get_job_persistence)],
    client: Annotated[Client, Depends(get_current_client)],
):
    try:
        job = await get_job_for_client(job_persistence, client.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    except ForbiddenJobError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    return AnalysisJobPublicView(
        id=job.id,
        status=JobStatus(job.status),
        content_type=job.content_type,
        size_bytes=int(job.size_bytes),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/analysis-jobs/{job_id}/report")
async def get_analysis_report(
    job_id: UUID,
    job_persistence: Annotated[UnitOfWork, Depends(get_job_persistence)],
    client: Annotated[Client, Depends(get_current_client)],
    report_reader: Annotated[TechnicalReportReaderPort, Depends(get_technical_report_reader)],
):
    try:
        job = await get_job_for_client(job_persistence, client.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    except ForbiddenJobError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    if job.status != JobStatus.ANALYZED.value:
        if job.status == JobStatus.ERROR.value:
            raise HTTPException(status.HTTP_409_CONFLICT, "Job failed")
        raise HTTPException(status.HTTP_425_TOO_EARLY, "Report not ready yet")

    try:
        return load_report_for_api(job, report_reader=report_reader)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report file missing")
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Report file is invalid or corrupted",
        ) from error


@router.get("/clients/me/token-balance", response_model=TokenBalanceResponse)
async def get_token_balance(client: Annotated[Client, Depends(get_current_client)]):
    return TokenBalanceResponse(token_balance=client.token_balance)
