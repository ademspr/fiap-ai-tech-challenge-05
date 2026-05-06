from sqlalchemy.ext.asyncio import AsyncSession

from hackathon_api.application.persistence import UnitOfWork
from hackathon_api.application.ports import JobRepositoryPort
from hackathon_api.infrastructure.repositories.jobs import SqlAlchemyJobRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Binds a single async SQLAlchemy session to repository instances and commit/rollback."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = SqlAlchemyJobRepository(session)

    @property
    def jobs(self) -> JobRepositoryPort:
        return self._jobs

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
