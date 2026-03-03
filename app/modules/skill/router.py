from uuid import UUID

from fastapi import APIRouter, Query

from app.core.database import DbSessionDep
from app.modules.skill.schemas import SkillOut
from app.modules.skill.service import SkillService
from app.shared.schemas import ApiResponse

router = APIRouter(prefix="/skill", tags=["Skill"])

@router.get("/{skill_id}", response_model=ApiResponse[SkillOut])
async def get_skill(
        skill_id: UUID,
        session: DbSessionDep,
        include_deleted: bool = Query(False, description="soft delete된 데이터 포함 여부"),
):
    service = SkillService(session)
    skill = await service.get(skill_id, include_deleted=include_deleted)
    return ApiResponse(data=SkillOut.model_validate(skill))