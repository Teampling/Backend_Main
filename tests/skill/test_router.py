from uuid import uuid4


def test_list_skills는_정상응답을_반환한다(client, mock_skill_service, make_skill):
    items = [
        make_skill(name="Python", img_url="https://example.com/python.png"),
        make_skill(name="PyTest", img_url="https://example.com/pytest.png"),
    ]
    mock_skill_service.list.return_value = {
        "items": items,
        "page": 1,
        "size": 10,
        "total": 2,
    }

    response = client.get(
        "/skills",
        params={
            "keyword": "py",
            "page": 1,
            "size": 10,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["code"] == "SKILL_LIST_FETCHED"
    assert body["message"] == "skill 목록 조회 성공"
    assert body["data"]["page"] == 1
    assert body["data"]["size"] == 10
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["name"] == "Python"
    assert body["data"]["items"][1]["name"] == "PyTest"

    mock_skill_service.list.assert_awaited_once_with(
        keyword="py",
        page=1,
        size=10,
        include_deleted=False,
    )

def test_list_skills는_page가_1미만이면_422를_반환한다(client, mock_skill_service):
    response = client.get("/skills", params={"page": 0})

    assert response.status_code == 422
    mock_skill_service.list.assert_not_called()

def test_list_skills는_size가_100초과이면_422를_반환한다(client, mock_skill_service):
    response = client.get("/skills", params={"size": 101})

    assert response.status_code == 422
    mock_skill_service.list.assert_not_called()

def test_get_skill은_정상응답을_반환한다(client, mock_skill_service, make_skill):
    skill = make_skill(name="Python", img_url="https://example.com/python.png")
    mock_skill_service.get.return_value = skill

    response = client.get(f"/skills/{skill.id}")

    assert response.status_code == 200

    body = response.json()
    assert body["code"] == "SKILL_FETCHED"
    assert body["message"] == "skill 조회 성공"
    assert body["data"]["id"] == str(skill.id)
    assert body["data"]["name"] == "Python"
    assert body["data"]["img_url"] == "https://example.com/python.png"

    mock_skill_service.get.assert_awaited_once_with(
        skill.id,
        include_deleted=False,
    )

def test_get_skill은_UUID형식이_아니면_422를_반환한다(client, mock_skill_service):
    response = client.get("/skills/not-a-uuid")

    assert response.status_code == 422
    mock_skill_service.get.assert_not_called()

def test_create_skill은_정상생성시_201을_반환한다(client, mock_skill_service, make_skill):
    created = make_skill(name="Python", img_url="https://example.com/python.png")
    mock_skill_service.create.return_value = created

    payload = {
        "name": "Python",
        "img_url": "https://example.com/python.png",
    }

    response = client.post("/skills", json=payload)

    assert response.status_code == 201

    body = response.json()
    assert body["code"] == "SKILL_CREATED"
    assert body["message"] == "skill 생성 성공"
    assert body["data"]["id"] == str(created.id)
    assert body["data"]["name"] == "Python"
    assert body["data"]["img_url"] == "https://example.com/python.png"

    mock_skill_service.create.assert_awaited_once()
    called_data = mock_skill_service.create.await_args.args[0]
    assert called_data.name == "Python"
    assert str(called_data.img_url) == "https://example.com/python.png"

def test_create_skill은_name이_없으면_422를_반환한다(client, mock_skill_service):
    payload = {
        "img_url": "https://example.com/python.png",
    }

    response = client.post("/skills", json=payload)

    assert response.status_code == 422
    mock_skill_service.create.assert_not_called()

def test_create_skill은_img_url형식이_잘못되면_422를_반환한다(client, mock_skill_service):
    payload = {
        "name": "Python",
        "img_url": "not-a-url",
    }

    response = client.post("/skills", json=payload)

    assert response.status_code == 422
    assert any(err["loc"][-1] == "img_url" for err in response.json()["detail"])
    mock_skill_service.create.assert_not_called()

def test_update_skill은_정상수정시_200을_반환한다(client, mock_skill_service, make_skill):
    skill_id = uuid4()
    updated = make_skill(
        skill_id=skill_id,
        name="PyTest",
        img_url="https://example.com/pytest.png",
    )
    mock_skill_service.update.return_value = updated

    payload = {
        "name": "PyTest",
        "img_url": "https://example.com/pytest.png",
    }

    response = client.patch(f"/skills/{skill_id}", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["code"] == "SKILL_UPDATED"
    assert body["message"] == "skill 수정 성공"
    assert body["data"]["id"] == str(skill_id)
    assert body["data"]["name"] == "PyTest"
    assert body["data"]["img_url"] == "https://example.com/pytest.png"

    mock_skill_service.update.assert_awaited_once()
    called_skill_id = mock_skill_service.update.await_args.args[0]
    called_data = mock_skill_service.update.await_args.args[1]

    assert called_skill_id == skill_id
    assert called_data.name == "PyTest"
    assert str(called_data.img_url) == "https://example.com/pytest.png"

def test_update_skill은_UUID형식이_아니면_422를_반환한다(client, mock_skill_service):
    payload = {
        "name": "PyTest",
        "img_url": "https://example.com/pytest.png",
    }

    response = client.patch("/skills/not-a-uuid", json=payload)

    assert response.status_code == 422
    mock_skill_service.update.assert_not_called()

def test_update_skill은_img_url형식이_잘못되면_422를_반환한다(client, mock_skill_service):
    skill_id = uuid4()
    payload = {
        "img_url": "invalid-url",
    }

    response = client.patch(f"/skills/{skill_id}", json=payload)

    assert response.status_code == 422
    assert any(err["loc"][-1] == "img_url" for err in response.json()["detail"])
    mock_skill_service.update.assert_not_called()

def test_delete_skill은_기본적으로_soft_delete를_수행한다(client, mock_skill_service):
    skill_id = uuid4()
    mock_skill_service.delete.return_value = None

    response = client.delete(f"/skills/{skill_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["code"] == "SKILL_DELETED"
    assert body["message"] == "skill 삭제 성공"
    assert body["data"] is None

    mock_skill_service.delete.assert_awaited_once_with(
        skill_id,
        hard=False,
    )

def test_restore_skill은_정상복구시_200을_반환한다(client, mock_skill_service, make_skill):
    skill_id = uuid4()
    restored = make_skill(
        skill_id=skill_id,
        name="Python",
        img_url="https://example.com/python.png",
    )
    mock_skill_service.restore.return_value = restored

    response = client.patch(f"/skills/{skill_id}/restore")

    assert response.status_code == 200

    body = response.json()
    assert body["code"] == "SKILL_RESTORED"
    assert body["message"] == "skill 복구 성공"
    assert body["data"]["id"] == str(skill_id)
    assert body["data"]["name"] == "Python"
    assert body["data"]["img_url"] == "https://example.com/python.png"

    mock_skill_service.restore.assert_awaited_once_with(skill_id)

def test_restore_skill은_UUID형식이_아니면_422를_반환한다(client, mock_skill_service):
    response = client.patch("/skills/not-a-uuid/restore")

    assert response.status_code == 422
    mock_skill_service.restore.assert_not_called()