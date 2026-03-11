from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings

local_engine = create_async_engine(settings.LOCAL_DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=local_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
)

docker_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

AsyncSessionDocker = async_sessionmaker(
    bind=docker_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionDocker() as session:
        yield session

DbSessionDep = Annotated[AsyncSession, Depends(get_session)]