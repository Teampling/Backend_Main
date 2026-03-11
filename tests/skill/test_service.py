from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.skill.modules import Skill
from app.modules.skill.schemas import SkillCreateIn, SkillUpdateIn


pytestmark = pytest.mark.asyncio

async def test_get은_존재하는_ID에_대해_스킬을_반환한다(skill_service):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_id.return_value = skill

    result = await skill_service.get(skill_id)

    assert result == skill
    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=False,
    )


async def test_get은_존재하지_않는_ID에_대해_not_found를_발생시킨다(skill_service):
    skill_id = uuid4()
    skill_service.repo.get_by_id.return_value = None

    with pytest.raises(AppError):
        await skill_service.get(skill_id)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=False,
    )


async def test_list는_repo의_조회결과와_카운트를_묶어서_반환한다(skill_service):
    items = [
        Skill(name="Python", img_url="https://example.com/python.png"),
        Skill(name="PyTorch", img_url="https://example.com/pytorch.png"),
    ]
    skill_service.repo.list.return_value = items
    skill_service.repo.count.return_value = 2

    result = await skill_service.list(page=1, size=10, keyword="py")

    assert result["items"] == items
    assert result["page"] == 1
    assert result["size"] == 10
    assert result["total"] == 2

    skill_service.repo.list.assert_awaited_once_with(
        keyword="py",
        offset=0,
        limit=10,
        include_deleted=False,
    )
    skill_service.repo.count.assert_awaited_once_with(
        keyword="py",
        include_deleted=False,
    )


async def test_list는_page가_1보다_작으면_1로_보정한다(skill_service):
    skill_service.repo.list.return_value = []
    skill_service.repo.count.return_value = 0

    result = await skill_service.list(page=0, size=10)

    assert result["page"] == 1
    skill_service.repo.list.assert_awaited_once_with(
        keyword=None,
        offset=0,
        limit=10,
        include_deleted=False,
    )


async def test_list는_size가_1보다_작으면_1로_보정한다(skill_service):
    skill_service.repo.list.return_value = []
    skill_service.repo.count.return_value = 0

    result = await skill_service.list(page=1, size=0)

    assert result["size"] == 1
    skill_service.repo.list.assert_awaited_once_with(
        keyword=None,
        offset=0,
        limit=1,
        include_deleted=False,
    )


async def test_list는_size가_100보다_크면_100으로_보정한다(skill_service):
    skill_service.repo.list.return_value = []
    skill_service.repo.count.return_value = 0

    result = await skill_service.list(page=1, size=999)

    assert result["size"] == 100
    skill_service.repo.list.assert_awaited_once_with(
        keyword=None,
        offset=0,
        limit=100,
        include_deleted=False,
    )


async def test_create는_같은_이름의_스킬이_이미_존재하면_bad_request를_발생시킨다(skill_service, mock_session):
    existing = Skill(
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_name.return_value = existing

    data = SkillCreateIn(
        name="Python",
        img_url="https://example.com/python-new.png",
    )

    with pytest.raises(AppError):
        await skill_service.create(data)

    skill_service.repo.get_by_name.assert_awaited_once_with("Python")
    skill_service.repo.save.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


async def test_create는_중복이_없으면_스킬을_저장하고_commit한다(skill_service, mock_session):
    saved = Skill(
        id=uuid4(),
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = saved

    data = SkillCreateIn(
        name="Python",
        img_url="https://example.com/python.png",
    )

    result = await skill_service.create(data)

    assert result == saved
    skill_service.repo.get_by_name.assert_awaited_once_with("Python")
    skill_service.repo.save.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(saved)


async def test_create는_save중_IntegrityError가_발생하면_rollback후_bad_request를_발생시킨다(
    skill_service,
    mock_session,
):
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))

    data = SkillCreateIn(
        name="Python",
        img_url="https://example.com/python.png",
    )

    with pytest.raises(AppError):
        await skill_service.create(data)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


async def test_update는_대상_스킬이_없으면_not_found를_발생시킨다(skill_service, mock_session):
    skill_id = uuid4()
    skill_service.repo.get_by_id.return_value = None

    data = SkillUpdateIn(name="FastAPI")

    with pytest.raises(AppError):
        await skill_service.update(skill_id, data)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=False,
    )
    mock_session.commit.assert_not_called()


async def test_update는_name이_patch에_없으면_중복이름_검사를_하지_않고_수정한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.save.return_value = skill

    data = SkillUpdateIn(
        img_url="https://example.com/python-new.png",
    )

    result = await skill_service.update(skill_id, data)

    assert result.img_url == "https://example.com/python-new.png"
    skill_service.repo.get_by_name.assert_not_called()
    skill_service.repo.save.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(skill)


async def test_update는_다른_스킬과_중복된_이름으로_변경하려고_하면_bad_request를_발생시킨다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    existing = Skill(
        id=uuid4(),
        name="React",
        img_url="https://example.com/react.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = existing

    data = SkillUpdateIn(name="React")

    with pytest.raises(AppError):
        await skill_service.update(skill_id, data)

    skill_service.repo.get_by_name.assert_awaited_once_with("React")
    skill_service.repo.save.assert_not_called()
    mock_session.commit.assert_not_called()


async def test_update는_같은_스킬_ID_데이터_내에서_같은_이름으로_수정하면_중복으로_보지_않고_수정한다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    existing_same_skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = existing_same_skill
    skill_service.repo.save.return_value = skill

    data = SkillUpdateIn(name="Python")

    result = await skill_service.update(skill_id, data)

    assert result == skill
    skill_service.repo.save.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(skill)


async def test_update는_정상수정시_patch값을_엔티티에_반영하고_commit한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    updated_skill = Skill(
        id=skill_id,
        name="FastAPI",
        img_url="https://example.com/fastapi.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = updated_skill

    data = SkillUpdateIn(
        name="FastAPI",
        img_url="https://example.com/fastapi.png",
    )

    result = await skill_service.update(skill_id, data)

    assert result == updated_skill
    assert skill.name == "FastAPI"
    assert skill.img_url == "https://example.com/fastapi.png"
    skill_service.repo.save.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(updated_skill)


async def test_update는_save중_IntegrityError가_발생하면_rollback후_bad_request를_발생시킨다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))

    data = SkillUpdateIn(name="FastAPI")

    with pytest.raises(AppError):
        await skill_service.update(skill_id, data)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


async def test_delete는_hard가_False이면_soft_delete를_호출하고_commit한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.soft_delete.return_value = skill

    await skill_service.delete(skill_id, hard=False)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    skill_service.repo.soft_delete.assert_awaited_once_with(skill)
    skill_service.repo.hard_delete.assert_not_called()
    mock_session.commit.assert_awaited_once()


async def test_delete는_hard가_True이면_hard_delete를_호출하고_commit한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )

    skill_service.repo.get_by_id.return_value = skill

    await skill_service.delete(skill_id, hard=True)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    skill_service.repo.hard_delete.assert_awaited_once_with(skill)
    skill_service.repo.soft_delete.assert_not_called()
    mock_session.commit.assert_awaited_once()


async def test_delete는_repo에서_예외가_발생하면_rollback한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.soft_delete.side_effect = RuntimeError("delete failed")

    with pytest.raises(RuntimeError):
        await skill_service.delete(skill_id, hard=False)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


async def test_restore는_대상이_없으면_not_found를_발생시킨다(skill_service, mock_session):
    skill_id = uuid4()
    skill_service.repo.get_by_id.return_value = None

    with pytest.raises(AppError):
        await skill_service.restore(skill_id)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    mock_session.commit.assert_not_called()


async def test_restore는_삭제된_상태가_아니면_bad_request를_발생시킨다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=False,
    )
    skill_service.repo.get_by_id.return_value = skill

    with pytest.raises(AppError):
        await skill_service.restore(skill_id)

    mock_session.commit.assert_not_called()


async def test_restore는_삭제된_스킬을_복구하고_commit한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True,
    )
    restored = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=False,
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.save.return_value = restored

    result = await skill_service.restore(skill_id)

    assert result == restored
    assert skill.is_deleted is False
    assert skill.deleted_at is None
    skill_service.repo.save.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(restored)


async def test_restore는_save중_IntegrityError가_발생하면_rollback후_bad_request를_발생시킨다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True,
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))

    with pytest.raises(AppError):
        await skill_service.restore(skill_id)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()