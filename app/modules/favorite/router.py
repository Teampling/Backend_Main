from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from app.modules.favorite.dependencies import FavoriteServiceDep
from app.modules.favorite.schemas import FavoriteOut
from app.modules.member.dependencies import CurrentMemberDep
from app.shared.schemas import ApiResponse

router = APIRouter(prefix="/favorite", tags=["Favorite"])


@router.post(
    path="/{project_id}",
    response_model=ApiResponse[FavoriteOut],
    summary="프로젝트 즐겨찾기",
    description="특정 프로젝트를 즐겨찾기에 추가하거나 이미 존재하면 삭제합니다.",
)
async def favorite_project(
    service: FavoriteServiceDep,
    current_member: CurrentMemberDep,
    project_id: Annotated[UUID, Path(..., description="프로젝트 ID")],
):
    is_favorite = await service.favorite(project_id, current_member.id)

    return ApiResponse.success(
        code="FAVORITE_UPDATED",
        message="즐겨찾기 상태 변경 성공",
        data=FavoriteOut(
            project_id=project_id,
            is_favorite=is_favorite,
        )
    )