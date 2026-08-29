from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.favorite.models import Favorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_project_member(self, project_id: UUID, member_id: UUID) -> Favorite | None:
        stmt = select(Favorite).where(
            Favorite.project_id == project_id,
            Favorite.member_id == member_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def create_favorite(self, favorite: Favorite) -> Favorite:
        self.session.add(favorite)
        await self.session.flush()
        return favorite

    async def delete_favorite(self, favorite: Favorite) -> None:
        await self.session.delete(favorite)
        await self.session.flush()