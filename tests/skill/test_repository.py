from uuid import uuid4

import pytest
from sqlmodel import select

from app.modules.skill.modules import Skill
from tests.conftest import skill_factory


pytestmark = pytest.mark.asyncio

async def test_save_호출_시_스킬이_DB에_저장된다(skill_repo, session):
    skill = Skill(
        name="Python",
        img_url="https://example.com/python.png",
    )

    saved = await skill_repo.save(skill)

    assert saved.id is not None
    assert saved.name == "Python"
    assert saved.img_url == "https://example.com/python.png"

    found = await session.scalar(
        select(Skill).where(Skill.id == saved.id)
    )
    assert found is not None
    assert found.id == saved.id
    assert found.name == "Python"
    assert found.img_url == "https://example.com/python.png"

async def test_ID로_조회하면_해당_스킬을_반환한다(skill_repo, skill_factory):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )

    found = await skill_repo.get_by_id(skill.id)

    assert found is not None
    assert found.id == skill.id
    assert found.name == "Python"
    assert found.img_url == "https://example.com/python.png"

async def test_존재하지_않는_ID로_조회하면_None을_반환한다(skill_repo):
    found = await skill_repo.get_by_id(uuid4())
    assert found is None

async def test_ID_기반_조회_시_include_deleted를_지정하지_않으면_삭제된_데이터를_조회하지_않는다(skill_repo, skill_factory):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True
    )

    found = await skill_repo.get_by_id(skill.id)

    assert found is None

async def test_ID_기반_조회_시_include_delete가_True면_삭제된_데이터도_조회한다(skill_repo, skill_factory):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True,
    )

    found = await skill_repo.get_by_id(skill.id, include_deleted=True)

    assert found is not None
    assert found.id == skill.id
    assert found.is_deleted is True

async def test_이름으로_조회하면_해당_스킬을_반환한다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )

    found = await skill_repo.get_by_name("Python")

    assert found is not None
    assert found.name == "Python"
    assert found.img_url == "https://example.com/python.png"


async def test_존재하지_않는_이름으로_조회하면_None을_반환한다(skill_repo):
    found = await skill_repo.get_by_name("Java")

    assert found is None


async def test_이름_기반_조회_시_include_deleted를_지정하지_않으면_삭제된_데이터를_조회하지_않는다(
    skill_repo,
    skill_factory,
):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True,
    )

    found = await skill_repo.get_by_name("Python")

    assert found is None


async def test_이름_기반_조회_시_include_deleted가_True면_삭제된_데이터도_조회한다(
    skill_repo,
    skill_factory,
):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
        is_deleted=True,
    )

    found = await skill_repo.get_by_name("Python", include_deleted=True)

    assert found is not None
    assert found.id == skill.id
    assert found.is_deleted is True


async def test_list는_삭제되지_않은_데이터만_이름_오름차순으로_반환한다(skill_repo, skill_factory):
    await skill_factory(
        name="React",
        img_url="https://example.com/react.png",
    )
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="Docker",
        img_url="https://example.com/docker.png",
        is_deleted=True,
    )

    result = await skill_repo.list()

    names = [skill.name for skill in result]

    assert names == ["Python", "React"]


async def test_list는_keyword가_주어지면_이름에_포함된_데이터만_반환한다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="Pytest",
        img_url="https://example.com/pytest.png",
    )
    await skill_factory(
        name="React",
        img_url="https://example.com/react.png",
    )

    result = await skill_repo.list(keyword="py")

    names = [skill.name for skill in result]

    assert names == ["Pytest", "Python"]


async def test_list는_offset과_limit을_적용한다(skill_repo, skill_factory):
    await skill_factory(
        name="A",
        img_url="https://example.com/a.png",
    )
    await skill_factory(
        name="B",
        img_url="https://example.com/b.png",
    )
    await skill_factory(
        name="C",
        img_url="https://example.com/c.png",
    )

    result = await skill_repo.list(offset=1, limit=1)

    assert len(result) == 1
    assert result[0].name == "B"


async def test_list는_include_deleted가_True면_삭제된_데이터도_포함한다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="Docker",
        img_url="https://example.com/docker.png",
        is_deleted=True,
    )

    result = await skill_repo.list(include_deleted=True)

    names = [skill.name for skill in result]

    assert names == ["Docker", "Python"]


async def test_count는_삭제되지_않은_데이터만_센다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="React",
        img_url="https://example.com/react.png",
    )
    await skill_factory(
        name="Docker",
        img_url="https://example.com/docker.png",
        is_deleted=True,
    )

    count = await skill_repo.count()

    assert count == 2


async def test_count는_keyword가_주어지면_조건에_맞는_데이터만_센다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="Pytest",
        img_url="https://example.com/pytest.png",
    )
    await skill_factory(
        name="React",
        img_url="https://example.com/react.png",
    )

    count = await skill_repo.count(keyword="py")

    assert count == 2


async def test_count는_include_deleted가_True면_삭제된_데이터도_포함한다(skill_repo, skill_factory):
    await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )
    await skill_factory(
        name="Docker",
        img_url="https://example.com/docker.png",
        is_deleted=True,
    )

    count = await skill_repo.count(include_deleted=True)

    assert count == 2


async def test_soft_delete를_호출하면_is_deleted가_True로_변경되고_deleted_at이_설정된다(
    skill_repo,
    skill_factory,
):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )

    deleted = await skill_repo.soft_delete(skill)

    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None


async def test_soft_delete된_데이터는_기본_조회에서_제외된다(skill_repo, skill_factory):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )

    await skill_repo.soft_delete(skill)

    found = await skill_repo.get_by_id(skill.id)

    assert found is None


async def test_hard_delete를_호출하면_DB에서_데이터가_완전히_삭제된다(
    skill_repo,
    skill_factory,
    session,
):
    skill = await skill_factory(
        name="Python",
        img_url="https://example.com/python.png",
    )

    await skill_repo.hard_delete(skill)

    found = await session.scalar(
        select(Skill).where(Skill.id == skill.id)
    )

    assert found is None