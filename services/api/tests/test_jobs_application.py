import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_tests_dir = Path(__file__).resolve().parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from support.tmp_storage import TmpFilesystemStorage

from hackathon_api.application.jobs import create_analysis_job, load_report_for_api
from hackathon_api.config import settings
from hackathon_api.domain.entities import AnalysisJob, Client
from hackathon_api.domain.exceptions import (
    MessagingFailedError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from hackathon_api.domain.policies import ALLOWED_CONTENT_TYPES, UploadPolicy
from hackathon_api.infrastructure.adapters.analyze_publisher import RabbitAnalyzeJobPublisher
from hackathon_api.infrastructure.adapters.pydantic_technical_report_reader import (
    PydanticTechnicalReportReader,
)
from hackathon_api.infrastructure.db.models import Base, ClientModel
from hackathon_api.infrastructure.messaging.bus import MessagePublisher
from hackathon_api.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def _policy(max_bytes: int | None = None) -> UploadPolicy:
    return UploadPolicy(
        allowed_content_types=ALLOWED_CONTENT_TYPES,
        max_upload_bytes=max_bytes or settings.max_upload_bytes,
        min_tokens_estimate=10,
    )


class _FailingPublisher(MessagePublisher):
    async def publish_json(self, routing_key: str, body: bytes) -> None:  # noqa: ARG002
        raise MessagingFailedError


class _InMemoryListPublisher(MessagePublisher):
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def publish_json(self, routing_key: str, body: bytes) -> None:
        self.messages.append((routing_key, body))


async def _engine_client_session(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    tmp_storage = TmpFilesystemStorage(tmp_path)

    session = session_factory()
    client_model = ClientModel(
        id=uuid4(),
        bearer_token_hash="x",
        bearer_token_prefix="x",
        name="t",
        token_balance=1000,
    )
    session.add(client_model)
    await session.commit()
    await session.refresh(client_model)
    return engine, session, client_model, tmp_storage


@pytest.mark.asyncio
async def test_create_analysis_job_rejects_unsupported_mime(tmp_path, monkeypatch):
    engine, session, client_model, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        job_persistence = SqlAlchemyUnitOfWork(session)
        with pytest.raises(UnsupportedMediaTypeError):
            await create_analysis_job(
                job_persistence,
                Client(id=client_model.id, token_balance=client_model.token_balance),
                file_storage=tmp_storage,
                analyze_publisher=RabbitAnalyzeJobPublisher(_InMemoryListPublisher()),
                policy=_policy(),
                filename="f.png",
                content_type="image/gif",
                data=b"x",
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_analysis_job_rejects_payload_too_large(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 5)
    engine, session, client_model, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        job_persistence = SqlAlchemyUnitOfWork(session)
        with pytest.raises(PayloadTooLargeError):
            await create_analysis_job(
                job_persistence,
                Client(id=client_model.id, token_balance=client_model.token_balance),
                file_storage=tmp_storage,
                analyze_publisher=RabbitAnalyzeJobPublisher(_InMemoryListPublisher()),
                policy=_policy(max_bytes=5),
                filename="f.png",
                content_type="image/png",
                data=b"123456",
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_analysis_job_propagates_messaging_failed(tmp_path, monkeypatch):
    engine, session, client_model, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        with pytest.raises(MessagingFailedError):
            await create_analysis_job(
                SqlAlchemyUnitOfWork(session),
                Client(id=client_model.id, token_balance=client_model.token_balance),
                file_storage=tmp_storage,
                analyze_publisher=RabbitAnalyzeJobPublisher(_FailingPublisher()),
                policy=_policy(),
                filename="f.png",
                content_type="image/png",
                data=b"x",
            )
    finally:
        await session.close()
        await engine.dispose()


class _PublisherRaisesRuntimeError(MessagePublisher):
    async def publish_json(self, routing_key: str, body: bytes) -> None:  # noqa: ARG002
        raise RuntimeError("broker io")


@pytest.mark.asyncio
async def test_create_analysis_job_wraps_broker_error_as_messaging_failed(tmp_path, monkeypatch):
    engine, session, client_model, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        with pytest.raises(MessagingFailedError) as exc_info:
            await create_analysis_job(
                SqlAlchemyUnitOfWork(session),
                Client(id=client_model.id, token_balance=client_model.token_balance),
                file_storage=tmp_storage,
                analyze_publisher=RabbitAnalyzeJobPublisher(_PublisherRaisesRuntimeError()),
                policy=_policy(),
                filename="f.png",
                content_type="image/png",
                data=b"x",
            )
        assert exc_info.value.__cause__ is not None
    finally:
        await session.close()
        await engine.dispose()


def _analyzed_job(
    report_path: str,
) -> AnalysisJob:
    now = datetime.now(UTC)
    jid = uuid4()
    return AnalysisJob(
        id=jid,
        client_id=uuid4(),
        status="ANALYZED",
        diagram_storage_path="u/x",
        report_storage_path=report_path,
        report_schema_version=1,
        content_type="image/png",
        size_bytes=1,
        diagram_checksum=None,
        report_checksum=None,
        tokens_used=0,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _report_reader(storage: TmpFilesystemStorage) -> PydanticTechnicalReportReader:
    return PydanticTechnicalReportReader(storage)


@pytest.mark.asyncio
async def test_load_report_json_invalid_bytes(tmp_path, monkeypatch):
    engine, session, _, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        bad_json_path = tmp_storage.reports_root / "bad.json"
        bad_json_path.write_text("not valid json {", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_report_for_api(
                _analyzed_job("bad.json"),
                report_reader=_report_reader(tmp_storage),
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_load_report_json_missing_file(tmp_path, monkeypatch):
    engine, session, _, tmp_storage = await _engine_client_session(tmp_path, monkeypatch)
    try:
        with pytest.raises(FileNotFoundError):
            load_report_for_api(
                _analyzed_job("nope-missing.json"), report_reader=_report_reader(tmp_storage)
            )
    finally:
        await session.close()
        await engine.dispose()
