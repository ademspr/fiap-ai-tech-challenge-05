from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from hackathon_api.application.jobs import authenticate_client
from hackathon_api.application.persistence import UnitOfWork
from hackathon_api.application.ports import (
    AnalyzeJobPublisherPort,
    ClientAuthenticatorPort,
    FileStoragePort,
    JobMetricsPort,
    TechnicalReportReaderPort,
)
from hackathon_api.config import settings
from hackathon_api.domain.entities import Client
from hackathon_api.domain.policies import ALLOWED_CONTENT_TYPES, UploadPolicy
from hackathon_api.infrastructure.adapters.analyze_publisher import RabbitAnalyzeJobPublisher
from hackathon_api.infrastructure.adapters.file_storage import LocalFileStorageAdapter
from hackathon_api.infrastructure.adapters.pydantic_technical_report_reader import (
    PydanticTechnicalReportReader,
)
from hackathon_api.infrastructure.db.session import get_session
from hackathon_api.infrastructure.observability.prometheus_job_metrics import PrometheusJobMetrics
from hackathon_api.infrastructure.security.sqlalchemy_client_authenticator import (
    SqlAlchemyClientAuthenticator,
)
from hackathon_api.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

_bearer = HTTPBearer(auto_error=False)

_file_storage = LocalFileStorageAdapter()
_report_reader = PydanticTechnicalReportReader(_file_storage)
_job_metrics = PrometheusJobMetrics()


def get_file_storage() -> FileStoragePort:
    return _file_storage


def get_technical_report_reader() -> TechnicalReportReaderPort:
    return _report_reader


def get_job_metrics() -> JobMetricsPort:
    return _job_metrics


def get_upload_policy() -> UploadPolicy:
    return UploadPolicy(
        allowed_content_types=ALLOWED_CONTENT_TYPES,
        max_upload_bytes=settings.max_upload_bytes,
        min_tokens_estimate=settings.min_tokens_estimate,
    )


def get_job_persistence(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_client_authenticator(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClientAuthenticatorPort:
    return SqlAlchemyClientAuthenticator(session)


def get_analyze_job_publisher(request: Request) -> AnalyzeJobPublisherPort:
    message_publisher = request.app.state.message_publisher
    if message_publisher is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Messaging unavailable",
        )
    return RabbitAnalyzeJobPublisher(message_publisher)


async def get_current_client(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    authenticator: Annotated[ClientAuthenticatorPort, Depends(get_client_authenticator)],
) -> Client:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing or invalid bearer token",
        )

    client = await authenticate_client(credentials.credentials, authenticator=authenticator)
    if client is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid bearer token",
        )

    return client


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    if not x_internal_token or x_internal_token != settings.internal_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid internal token")
