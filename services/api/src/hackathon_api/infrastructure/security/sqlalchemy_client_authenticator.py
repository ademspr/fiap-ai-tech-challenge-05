from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hackathon_api.domain.entities import Client
from hackathon_api.infrastructure.db.models import ClientModel
from hackathon_api.infrastructure.mappers import client_from_model
from hackathon_api.infrastructure.security.bearer import token_prefix, verify_bearer_token


class SqlAlchemyClientAuthenticator:
    """Infrastructure adapter: maps bearer secret lookup + hash verify to domain Client."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate_bearer(self, bearer_plain: str) -> Client | None:
        prefix = token_prefix(bearer_plain)
        statement = select(ClientModel).where(ClientModel.bearer_token_prefix == prefix)
        result = await self._session.execute(statement)

        for row in result.scalars().all():
            if verify_bearer_token(bearer_plain, row.bearer_token_hash):
                return client_from_model(row)

        return None
