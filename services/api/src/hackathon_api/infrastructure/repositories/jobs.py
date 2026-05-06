from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hackathon_api.domain.entities import AnalysisJob
from hackathon_api.domain.enums import JobStatus
from hackathon_api.domain.exceptions import (
    ForbiddenJobError,
    JobNotFoundError,
)
from hackathon_api.infrastructure.db.models import AnalysisJobModel, ClientModel
from hackathon_api.infrastructure.mappers import analysis_job_from_model, client_from_model


class SqlAlchemyJobRepository:
    """ORM-backed job persistence; session is injected (one repository per request / UoW)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, job_id: UUID) -> AnalysisJob | None:
        statement = select(AnalysisJobModel).where(AnalysisJobModel.id == job_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return analysis_job_from_model(model)

    async def get_for_client(self, client_id: UUID, job_id: UUID) -> AnalysisJob:
        statement = (
            select(AnalysisJobModel)
            .options(selectinload(AnalysisJobModel.client))
            .where(AnalysisJobModel.id == job_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            raise JobNotFoundError
        if model.client_id != client_id:
            raise ForbiddenJobError

        return analysis_job_from_model(model)

    async def create_received(
        self,
        *,
        client_id: UUID,
        content_type: str,
        size_bytes: int,
    ) -> AnalysisJob:
        model = AnalysisJobModel(
            client_id=client_id,
            status=JobStatus.RECEIVED.value,
            diagram_storage_path="",
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self._session.add(model)
        await self._session.flush()
        return analysis_job_from_model(model)

    async def set_diagram(
        self,
        job_id: UUID,
        diagram_storage_path: str,
        diagram_checksum: str,
    ) -> AnalysisJob:
        model = await self._session.get(AnalysisJobModel, job_id)
        if model is None:
            raise JobNotFoundError
        model.diagram_storage_path = diagram_storage_path
        model.diagram_checksum = diagram_checksum
        return analysis_job_from_model(model)

    async def apply_status_patch(
        self,
        job_id: UUID,
        status: str,
        error_message: str | None,
    ) -> None:
        model = await self._session.get(AnalysisJobModel, job_id)
        if model is None:
            raise JobNotFoundError
        model.status = status
        model.error_message = error_message
        model.updated_at = datetime.now(UTC)

    async def complete_with_report(
        self,
        job_id: UUID,
        *,
        report_storage_path: str,
        tokens_used: int,
        report_checksum: str | None,
        report_schema_version: int,
    ) -> None:
        model = await self._session.get(AnalysisJobModel, job_id)
        if model is None:
            raise JobNotFoundError

        if model.status == JobStatus.ANALYZED.value:
            return

        statement = select(ClientModel).where(ClientModel.id == model.client_id).with_for_update()
        result = await self._session.execute(statement)
        client_row = result.scalar_one()

        debited = client_from_model(client_row).debited(tokens_used)
        client_row.token_balance = debited.token_balance

        model.status = JobStatus.ANALYZED.value
        model.report_storage_path = report_storage_path
        model.tokens_used = tokens_used
        model.report_checksum = report_checksum
        model.report_schema_version = report_schema_version
        model.updated_at = datetime.now(UTC)
        model.error_message = None
