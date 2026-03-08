from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Path, status

from app.core.database import DbSessionDep
from app.modules.skill.schemas import SkillOut, SkillCreateIn, SkillUpdateIn
from app.modules.skill.service import SkillService
from app.shared.schemas import ApiResponse, PageOut

router = APIRouter(prefix="/skills", tags=["Skill"])

@router.get(
    "",
    response_model=ApiResponse[PageOut[SkillOut]],
    summary="스킬 목록 조회",
    description="키워드, 페이지, 사이즈 조건으로 스킬 목록을 조회합니다.",
)
async def list_skills(
    session: DbSessionDep,
    keyword: Annotated[str | None, Query(description="검색 키워드", example="Java")] = None,
    page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
    include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    service = SkillService(session)
    result = await service.list(
        keyword=keyword,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    return ApiResponse(
        code="SKILL_LIST_FETCHED",
        message="skill 목록 조회 성공",
        data=PageOut[SkillOut](
            items=[SkillOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        ),
    )

@router.get(
    "/{skill_id}",
    response_model=ApiResponse[SkillOut],
    summary="스킬 단건 조회",
    description="skill ID에 해당하는 스킬의 상세 정보를 조회합니다.",
)
async def get_skill(
        session: DbSessionDep,
        skill_id: Annotated[UUID, Path(..., description="조회할 skill의 ID")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    service = SkillService(session)
    skill = await service.get(skill_id, include_deleted=include_deleted)
    return ApiResponse.success(
        code="SKILL_FETCHED",
        message="skill 조회 성공",
        data=SkillOut.model_validate(skill)
    )

@router.post(
    "",
    response_model=ApiResponse[SkillOut],
    status_code=status.HTTP_201_CREATED,
    summary="스킬 생성",
    description="새로운 스킬을 생성합니다.",
)
async def create_skill(
    data: SkillCreateIn,
    session: DbSessionDep,
):
    service = SkillService(session)
    created = await service.create(data)
    return ApiResponse.success(
        code="SKILL_CREATED",
        message="skill 생성 성공",
        data=SkillOut.model_validate(created)
    )

@router.patch(
    "/{skill_id}",
    response_model=ApiResponse[SkillOut],
    summary="스킬 수정",
    description="기존 스킬 정보를 부분 수정합니다.",
)
async def update_skill(
    data: SkillUpdateIn,
    session: DbSessionDep,
    skill_id: Annotated[UUID, Path(description="수정할 skill의 ID")],
):
    service = SkillService(session)
    updated = await service.update(skill_id, data)
    return ApiResponse.success(
        code="SKILL_UPDATED",
        message="skill 수정 성공",
        data=SkillOut.model_validate(updated),
    )


@router.delete(
    "/{skill_id}",
    response_model=ApiResponse[None],
    summary="스킬 삭제",
    description="기존 스킬을 삭제합니다. hard=true이면 완전 삭제, false이면 soft delete 처리합니다.",
)
async def delete_skill(
    session: DbSessionDep,
    skill_id: Annotated[UUID, Path(description="삭제할 skill의 ID")],
    hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete", example=False)] = False,
):
    service = SkillService(session)
    await service.delete(skill_id, hard=hard)
    return ApiResponse.success(
        code="SKILL_DELETED",
        message="skill 삭제 성공",
        data=None
    )

@router.patch(
    "/{skill_id}/restore",
    response_model=ApiResponse[SkillOut],
    summary="스킬 복구",
    description="soft delete 된 스킬을 복구합니다."
)
async def restore_skill(
        session: DbSessionDep,
        skill_id: Annotated[UUID, Path(description="복구할 skill ID")],
):
    service = SkillService(session)
    restored = await service.restore(skill_id)
    return ApiResponse.success(
        code="SKILL_RESTORED",
        message="skill 복구 성공",
        data=SkillOut.model_validate(restored)
    )