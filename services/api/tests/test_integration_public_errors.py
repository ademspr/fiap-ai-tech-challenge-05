from uuid import UUID, uuid4

import pytest
from hackathon_contracts import (
    ArchitecturalRisk,
    BasicRecommendation,
    IdentifiedComponent,
    TechnicalReportV1,
)

from hackathon_api.infrastructure.storage import local_files


@pytest.mark.asyncio
async def test_missing_bearer_returns_401(client_and_publisher):
    async_client, _, _, _ = client_and_publisher
    response = await async_client.get("/v1/clients/me/token-balance")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_bearer_returns_401(client_and_publisher):
    async_client, _, _, _ = client_and_publisher
    response = await async_client.get(
        "/v1/clients/me/token-balance",
        headers={"Authorization": "Bearer totally-wrong-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unsupported_media_type_upload(client_and_publisher, mini_png):
    async_client, _, token, _ = client_and_publisher
    files = {"file": ("x.gif", mini_png, "image/gif")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_without_filename_rejected(client_and_publisher, mini_png):
    async_client, _, token, _ = client_and_publisher
    files = {"file": ("", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    # FastAPI validates multipart before the route; empty filename may be 422.
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_upload_insufficient_token_balance_402(client_with_low_token_balance, mini_png):
    async_client, _, token, _ = client_with_low_token_balance
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 402


@pytest.mark.asyncio
async def test_upload_messaging_failed_503(client_failing_publisher, mini_png):
    async_client, token, _ = client_failing_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_job_not_found_404(client_and_publisher):
    async_client, _, token, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.get(
        f"/v1/analysis-jobs/{unknown_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_forbidden_other_client(two_clients_client_and_publisher, mini_png):
    async_client, _, token_a, token_b, _ = two_clients_client_and_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_report_too_early_425(client_and_publisher, mini_png):
    async_client, _, token, _ = client_and_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 425


@pytest.mark.asyncio
async def test_get_report_job_failed_409(client_and_publisher, mini_png, internal_headers):
    async_client, _, token, _ = client_and_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{job_id}",
        json={"status": "ERROR", "error_message": "boom"},
        headers=internal_headers,
    )
    assert response.status_code == 200

    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_report_file_missing_404(client_and_publisher, mini_png, internal_headers):
    async_client, _, token, tmp_storage = client_and_publisher
    files = {"file": ("x.png", mini_png, "image/png")}
    response = await async_client.post(
        "/v1/analysis-jobs",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    job_id = UUID(response.json()["id"])

    report = TechnicalReportV1(
        schema_version=1,
        identified_components=[
            IdentifiedComponent(id="c1", name="n", description="d"),
        ],
        architectural_risks=[
            ArchitecturalRisk(id="r1", title="t", description="d", severity="low"),
        ],
        basic_recommendations=[
            BasicRecommendation(id="b1", title="t", description="d"),
        ],
        tokens_used=3,
    )
    report_relative_name = local_files.relative_report_path(job_id)
    report_path = tmp_storage.reports_root / report_relative_name
    report_path.write_text(report.model_dump_json(), encoding="utf-8")

    await async_client.patch(
        f"/internal/v1/analysis-jobs/{job_id}",
        json={"status": "PROCESSING"},
        headers=internal_headers,
    )
    response = await async_client.post(
        f"/internal/v1/analysis-jobs/{job_id}/completion",
        json={
            "report_storage_path": report_relative_name,
            "tokens_used": 3,
            "report_schema_version": 1,
        },
        headers=internal_headers,
    )
    assert response.status_code == 200

    report_path.unlink()
    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
