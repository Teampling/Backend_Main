from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.skill.models import Skill
from app.modules.skill.schemas import SkillCreateIn, SkillUpdateIn


pytestmark = pytest.mark.asyncio

# --------------------
# get
# --------------------

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

# --------------------
# list
# --------------------

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

# --------------------
# create
# --------------------

async def test_create는_같은_이름의_스킬이_이미_존재하면_bad_request를_발생시킨다(skill_service, mock_session):
    existing = Skill(
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_name.return_value = existing

    data = SkillCreateIn(
        name="Python",
    )

    with pytest.raises(AppError):
        await skill_service.create(data)

    skill_service.repo.get_by_name.assert_awaited_once_with("Python")
    skill_service.repo.save.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


async def test_create는_파일이_없으면_업로드없이_스킬을_저장하고_commit한다(skill_service, mock_session):
    saved = Skill(
        id=uuid4(),
        name="Python",
        img_url=None,
    )
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = saved

    data = SkillCreateIn(name="Python")

    result = await skill_service.create(data)

    assert result == saved
    skill_service.repo.get_by_name.assert_awaited_once_with("Python")
    skill_service.storage.upload_object.assert_not_called()
    skill_service.storage.build_object_url.assert_not_called()
    skill_service.repo.save.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(saved)


async def test_create는_파일이_있으면_업로드후_img_url을_세팅하고_저장한다(skill_service, mock_session):
    saved = Skill(
        id=uuid4(),
        name="Python",
        img_url="https://cdn.example.com/skill/python.png",
    )
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = saved
    skill_service.storage.upload_object.return_value = "skill/python.png"
    skill_service.storage.build_object_url.return_value = "https://cdn.example.com/skill/python.png"

    data = SkillCreateIn(name="Python")
    icon_file = UploadFile(filename="python.png", file=BytesIO(b"fake-image"))

    result = await skill_service.create(data, icon_file=icon_file)

    assert result == saved
    skill_service.storage.upload_object.assert_awaited_once()
    skill_service.storage.build_object_url.assert_called_once_with("skill/python.png")
    skill_service.repo.save.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(saved)


async def test_create는_save중_IntegrityError가_발생하면_rollback후_업로드한_이미지를_삭제한다(
    skill_service,
    mock_session,
):
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))
    skill_service.storage.upload_object.return_value = "skill/python.png"
    skill_service.storage.build_object_url.return_value = "https://cdn.example.com/skill/python.png"

    data = SkillCreateIn(name="Python")
    icon_file = UploadFile(filename="python.png", file=BytesIO(b"fake-image"))

    with pytest.raises(AppError):
        await skill_service.create(data, icon_file=icon_file)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
    skill_service.storage.delete_object.assert_awaited_once_with("skill/python.png")


async def test_create는_save중_IntegrityError가_발생해도_업로드한_이미지가_없으면_삭제를_시도하지_않는다(
    skill_service,
    mock_session,
):
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))

    data = SkillCreateIn(name="Python")

    with pytest.raises(AppError):
        await skill_service.create(data)

    mock_session.rollback.assert_awaited_once()
    skill_service.storage.delete_object.assert_not_called()


# --------------------
# update
# --------------------

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
    skill_service.storage.upload_object.assert_not_called()
    mock_session.commit.assert_not_called()


async def test_update는_같은_스킬_ID의_같은_이름으로_수정하면_중복으로_보지_않는다(
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


async def test_update는_파일이_없으면_이미지가_삭제된다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = skill

    data = SkillUpdateIn(name="FastAPI")

    result = await skill_service.update(skill_id, data)

    assert result == skill
    assert skill.name == "FastAPI"
    assert skill.img_url is None
    skill_service.storage.upload_object.assert_not_called()
    skill_service.storage.delete_object.assert_awaited_once()
    skill_service.repo.save.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(skill)


async def test_update는_새_파일이_있으면_업로드후_DB성공뒤_기존이미지를_삭제한다(skill_service, mock_session):
    skill_id = uuid4()
    old_url = "https://cdn.example.com/skill/old.png"
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=old_url,
    )
    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = skill
    skill_service.storage.upload_object.return_value = "skill/new.png"
    skill_service.storage.build_object_url.return_value = "https://cdn.example.com/skill/new.png"
    skill_service.storage.extract_object_name.return_value = "skill/old.png"

    data = SkillUpdateIn(name="FastAPI")
    icon_file = UploadFile(filename="new.png", file=BytesIO(b"fake-image"))

    result = await skill_service.update(skill_id, data, icon_file=icon_file)

    assert result == skill
    assert skill.name == "FastAPI"
    assert skill.img_url == "https://cdn.example.com/skill/new.png"

    skill_service.storage.upload_object.assert_awaited_once()
    skill_service.storage.build_object_url.assert_called_once_with("skill/new.png")
    skill_service.storage.extract_object_name.assert_called_once_with(old_url)
    skill_service.storage.delete_object.assert_awaited_once_with("skill/old.png")
    mock_session.commit.assert_awaited_once()


async def test_update는_이전이미지가_없고_새_파일이_있으면_업로드만_하고_기존이미지_삭제는_안한다(skill_service, mock_session):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=None,
    )
    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.return_value = skill
    skill_service.storage.upload_object.return_value = "skill/new.png"
    skill_service.storage.build_object_url.return_value = "https://cdn.example.com/skill/new.png"

    data = SkillUpdateIn(name="FastAPI")
    icon_file = UploadFile(filename="new.png", file=BytesIO(b"fake-image"))

    result = await skill_service.update(skill_id, data, icon_file=icon_file)

    assert result == skill
    assert skill.img_url == "https://cdn.example.com/skill/new.png"

    skill_service.storage.upload_object.assert_awaited_once()
    skill_service.storage.delete_object.assert_not_called()


async def test_update는_save중_IntegrityError가_발생하면_rollback후_새로업로드한_이미지를_삭제한다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://cdn.example.com/skill/old.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))
    skill_service.storage.upload_object.return_value = "skill/new.png"
    skill_service.storage.build_object_url.return_value = "https://cdn.example.com/skill/new.png"

    data = SkillUpdateIn(name="FastAPI")
    icon_file = UploadFile(filename="new.png", file=BytesIO(b"fake-image"))

    with pytest.raises(AppError):
        await skill_service.update(skill_id, data, icon_file=icon_file)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
    skill_service.storage.delete_object.assert_awaited_once_with("skill/new.png")


async def test_update는_파일이_없을때_save중_IntegrityError가_발생하면_rollback만_수행한다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url="https://cdn.example.com/skill/old.png",
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.get_by_name.return_value = None
    skill_service.repo.save.side_effect = IntegrityError("stmt", "params", Exception("orig"))

    data = SkillUpdateIn(name="FastAPI")

    with pytest.raises(AppError):
        await skill_service.update(skill_id, data)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
    skill_service.storage.delete_object.assert_not_called()

# --------------------
# delete
# --------------------

async def test_delete는_hard가_False이면_soft_delete를_호출하고_commit하며_이미지는_삭제하지_않는다(
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
    skill_service.repo.soft_delete.return_value = skill

    await skill_service.delete(skill_id, hard=False)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    skill_service.repo.soft_delete.assert_awaited_once_with(skill)
    skill_service.repo.hard_delete.assert_not_called()
    skill_service.storage.extract_object_name.assert_not_called()
    skill_service.storage.delete_object.assert_not_called()
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_called()


async def test_delete는_hard가_True이고_이미지가_있으면_commit후_이미지도_삭제한다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    image_url = "https://example.com/python.png"
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=image_url,
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.storage.extract_object_name.return_value = "skill/python.png"

    await skill_service.delete(skill_id, hard=True)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    skill_service.repo.hard_delete.assert_awaited_once_with(skill)
    skill_service.repo.soft_delete.assert_not_called()
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_called()

    skill_service.storage.extract_object_name.assert_called_once_with(image_url)
    skill_service.storage.delete_object.assert_awaited_once_with("skill/python.png")


async def test_delete는_hard가_True여도_이미지가_없으면_스토리지삭제를_하지_않는다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=None,
    )

    skill_service.repo.get_by_id.return_value = skill

    await skill_service.delete(skill_id, hard=True)

    skill_service.repo.hard_delete.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    skill_service.storage.extract_object_name.assert_not_called()
    skill_service.storage.delete_object.assert_not_called()


async def test_delete는_이미지삭제에_실패해도_DB삭제는_성공으로_끝난다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    image_url = "https://example.com/python.png"
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=image_url,
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.storage.extract_object_name.return_value = "skill/python.png"
    skill_service.storage.delete_object.side_effect = RuntimeError("oci delete failed")

    await skill_service.delete(skill_id, hard=True)

    skill_service.repo.hard_delete.assert_awaited_once_with(skill)
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_called()
    skill_service.storage.extract_object_name.assert_called_once_with(image_url)
    skill_service.storage.delete_object.assert_awaited_once_with("skill/python.png")


async def test_delete는_hard_delete중_예외가_발생하면_rollback하고_이미지삭제도_하지_않는다(
    skill_service,
    mock_session,
):
    skill_id = uuid4()
    image_url = "https://example.com/python.png"
    skill = Skill(
        id=skill_id,
        name="Python",
        img_url=image_url,
    )

    skill_service.repo.get_by_id.return_value = skill
    skill_service.repo.hard_delete.side_effect = RuntimeError("hard delete failed")

    with pytest.raises(RuntimeError):
        await skill_service.delete(skill_id, hard=True)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
    skill_service.storage.extract_object_name.assert_not_called()
    skill_service.storage.delete_object.assert_not_called()


async def test_delete는_대상이_없으면_not_found를_발생시킨다(skill_service, mock_session):
    skill_id = uuid4()
    skill_service.repo.get_by_id.return_value = None

    with pytest.raises(AppError):
        await skill_service.delete(skill_id, hard=False)

    skill_service.repo.get_by_id.assert_awaited_once_with(
        skill_id,
        include_deleted=True,
    )
    skill_service.repo.soft_delete.assert_not_called()
    skill_service.repo.hard_delete.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


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