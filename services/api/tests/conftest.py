import base64
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("INTERNAL_TOKEN", "test-internal-token")

from hackathon_api.config import settings
from hackathon_api.domain.exceptions import MessagingFailedError
from hackathon_api.infrastructure.db.models import Base, ClientModel
from hackathon_api.infrastructure.db.session import get_session
from hackathon_api.infrastructure.messaging.bus import MessagePublisher
from hackathon_api.infrastructure.security.bearer import hash_bearer_token, token_prefix
from hackathon_api.main import create_app

MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class ListPublisher(MessagePublisher):
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def publish_json(self, routing_key: str, body: bytes) -> None:
        self.messages.append((routing_key, body))


class FailingListPublisher(MessagePublisher):
    async def publish_json(self, routing_key: str, body: bytes) -> None:  # noqa: ARG002
        raise MessagingFailedError


@pytest_asyncio.fixture
async def client_and_publisher(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    uploads = tmp_path / "uploads"
    reports = tmp_path / "reports"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    publisher = ListPublisher()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    plain_token = "test-bearer-secret-token-xyz"
    async with session_factory() as session:
        client_model = ClientModel(
            id=uuid4(),
            bearer_token_hash=hash_bearer_token(plain_token),
            bearer_token_prefix=token_prefix(plain_token),
            name="tester",
            token_balance=1000,
        )
        session.add(client_model)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state.message_publisher = publisher

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client, publisher, plain_token

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client_failing_publisher(monkeypatch, tmp_path: Path):
    """Same as client_and_publisher but queue publish always fails (503 on upload)."""
    db_path = tmp_path / "fail.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    uploads = tmp_path / "uploads_f"
    reports = tmp_path / "reports_f"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    publisher = FailingListPublisher()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    plain_token = "test-bearer-fail-publisher-token"
    async with session_factory() as session:
        client_model = ClientModel(
            id=uuid4(),
            bearer_token_hash=hash_bearer_token(plain_token),
            bearer_token_prefix=token_prefix(plain_token),
            name="tester",
            token_balance=1000,
        )
        session.add(client_model)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state.message_publisher = publisher

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client, plain_token

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def two_clients_client_and_publisher(monkeypatch, tmp_path: Path):
    """Two distinct clients: token_a and token_b for cross-tenant tests."""
    db_path = tmp_path / "test2.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    uploads = tmp_path / "uploads2"
    reports = tmp_path / "reports2"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    publisher = ListPublisher()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    token_a = "bearer-for-client-a-aaaaaaaaaa"
    token_b = "bearer-for-client-b-bbbbbbbbbb"
    async with session_factory() as session:
        for plain in (token_a, token_b):
            client_model = ClientModel(
                id=uuid4(),
                bearer_token_hash=hash_bearer_token(plain),
                bearer_token_prefix=token_prefix(plain),
                name="tester",
                token_balance=1000,
            )
            session.add(client_model)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state.message_publisher = publisher

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client, publisher, token_a, token_b

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client_with_low_token_balance(monkeypatch, tmp_path: Path):
    """Client with token_balance 0 so upload is blocked (min estimate default 10)."""
    db_path = tmp_path / "low.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    uploads = tmp_path / "uploads_l"
    reports = tmp_path / "reports_l"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    publisher = ListPublisher()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    plain_token = "low-balance-client-token-zzzz"
    async with session_factory() as session:
        client_model = ClientModel(
            id=uuid4(),
            bearer_token_hash=hash_bearer_token(plain_token),
            bearer_token_prefix=token_prefix(plain_token),
            name="poor",
            token_balance=0,
        )
        session.add(client_model)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state.message_publisher = publisher

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client, publisher, plain_token

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def internal_headers() -> dict[str, str]:
    return {"X-Internal-Token": "test-internal-token"}


@pytest.fixture
def mini_png() -> bytes:
    return MINI_PNG
