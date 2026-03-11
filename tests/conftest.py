from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings
from app.modules.skill.modules import Skill
from app.modules.skill.repository import SkillRepository


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        settings.LOCAL_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest_asyncio.fixture
async def session(engine):
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    return session

@pytest_asyncio.fixture
async def skill_repo(session: AsyncSession):
    from app.modules.skill.repository import SkillRepository
    return SkillRepository(session)

@pytest_asyncio.fixture
async def skill_service(mock_session: AsyncSession):
    from app.modules.skill.service import SkillService
    service = SkillService(mock_session)
    service.repo = AsyncMock(spec=SkillRepository)
    return service

@pytest_asyncio.fixture
async def skill_factory(session: AsyncSession):
    async def _create(
            *,
            name: str,
            img_url: str,
            is_deleted: bool = False,
    ) -> Skill:
        skill = Skill(
            name=name,
            img_url=img_url,
            is_deleted=is_deleted,
        )
        session.add(skill)
        await session.flush()
        await session.refresh(skill)
        return skill
    return _create