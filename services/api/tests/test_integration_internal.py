from uuid import UUID, uuid4

import pytest
from hackathon_contracts import (
    ArchitecturalRisk,
    BasicRecommendation,
    IdentifiedComponent,
    TechnicalReportV1,
)

from hackathon_api.config import settings
from hackathon_api.infrastructure.storage import local_files


@pytest.mark.asyncio
async def test_internal_patch_wrong_token_403(client_and_publisher):
    async_client, _, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{unknown_job_id}",
        json={"status": "PROCESSING"},
        headers={"X-Internal-Token": "not-the-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_internal_completion_wrong_token_403(client_and_publisher):
    async_client, _, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.post(
        f"/internal/v1/analysis-jobs/{unknown_job_id}/completion",
        json={
            "report_storage_path": f"{unknown_job_id}.json",
            "tokens_used": 1,
            "report_schema_version": 1,
        },
        headers={"X-Internal-Token": "bad"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_internal_patch_invalid_status_400(client_and_publisher, mini_png, internal_headers):
    async_client, _, token = client_and_publisher
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
        json={"status": "RECEIVED"},
        headers=internal_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_internal_patch_not_found_404(client_and_publisher, internal_headers):
    async_client, _, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{unknown_job_id}",
        json={"status": "PROCESSING"},
        headers=internal_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_internal_completion_not_found_404(client_and_publisher, internal_headers):
    async_client, _, _ = client_and_publisher
    unknown_job_id = uuid4()
    response = await async_client.post(
        f"/internal/v1/analysis-jobs/{unknown_job_id}/completion",
        json={
            "report_storage_path": f"{unknown_job_id}.json",
            "tokens_used": 1,
            "report_schema_version": 1,
        },
        headers=internal_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_internal_completion_insufficient_tokens_402(
    client_and_publisher, mini_png, internal_headers
):
    async_client, _, token = client_and_publisher
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
        tokens_used=0,
    )
    report_relative_name = local_files.relative_report_path(job_id)
    report_path = settings.reports_dir / report_relative_name
    report_path.write_text(report.model_dump_json(), encoding="utf-8")

    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{job_id}",
        json={"status": "PROCESSING"},
        headers=internal_headers,
    )
    assert response.status_code == 200

    response = await async_client.post(
        f"/internal/v1/analysis-jobs/{job_id}/completion",
        json={
            "report_storage_path": report_relative_name,
            "tokens_used": 9_000,
            "report_schema_version": 1,
        },
        headers=internal_headers,
    )
    assert response.status_code == 402

    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] != "ANALYZED"
