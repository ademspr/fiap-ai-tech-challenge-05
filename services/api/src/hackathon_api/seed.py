"""Create a demo client and print the bearer token once. Run: uv run python -m hackathon_api.seed"""

import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hackathon_api.config import settings
from hackathon_api.infrastructure.db.models import ClientModel
from hackathon_api.infrastructure.security.bearer import (
    generate_bearer_token,
    hash_bearer_token,
    token_prefix,
)


async def main() -> None:
    name = os.environ.get("SEED_CLIENT_NAME", "demo")
    initial_balance = int(os.environ.get("SEED_TOKEN_BALANCE", "100000"))
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    plain = generate_bearer_token()
    async with session_factory() as session:
        client = ClientModel(
            bearer_token_hash=hash_bearer_token(plain),
            bearer_token_prefix=token_prefix(plain),
            name=name,
            token_balance=initial_balance,
        )
        session.add(client)
        await session.commit()
        await session.refresh(client)

    print(f"client_id={client.id}")
    print(f"bearer_token={plain}")
    print("Store the bearer token securely; it cannot be retrieved again.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
