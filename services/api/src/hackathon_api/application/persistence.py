"""Unit-of-work port for persisting analysis jobs."""

from typing import Protocol

from hackathon_api.application.ports import JobRepositoryPort


class UnitOfWork(Protocol):
    """Transaction boundary for job persistence (commit / rollback in the adapter)."""

    @property
    def jobs(self) -> JobRepositoryPort: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
