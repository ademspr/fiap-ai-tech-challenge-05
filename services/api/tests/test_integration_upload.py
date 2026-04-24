import pytest


@pytest.mark.asyncio
async def test_upload_creates_job_and_publishes(client_and_publisher, mini_png):
    async_client, publisher, token = client_and_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post("/v1/analysis-jobs", files=files, headers=headers)
    assert response.status_code == 201, response.text
    assert "Location" in response.headers
    body = response.json()
    assert body["status"] == "RECEIVED"
    assert len(publisher.messages) == 1


@pytest.mark.asyncio
async def test_token_balance(client_and_publisher):
    async_client, _, token = client_and_publisher
    response = await async_client.get(
        "/v1/clients/me/token-balance", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["token_balance"] == 1000


@pytest.mark.asyncio
async def test_internal_patch_requires_token(client_and_publisher):
    from uuid import uuid4

    async_client, _, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{unknown_job_id}",
        json={"status": "PROCESSING"},
    )
    assert response.status_code == 403
