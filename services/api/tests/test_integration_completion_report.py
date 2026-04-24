from uuid import UUID

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
async def test_worker_completion_and_get_report(client_and_publisher, mini_png):
    async_client, _, token = client_and_publisher
    auth = {"Authorization": f"Bearer {token}"}
    internal_headers = {"X-Internal-Token": "test-internal-token"}
    files = {"file": ("x.png", mini_png, "image/png")}

    response = await async_client.post("/v1/analysis-jobs", files=files, headers=auth)
    assert response.status_code == 201, response.text
    job_id = UUID(response.json()["id"])

    report = TechnicalReportV1(
        schema_version=1,
        identified_components=[
            IdentifiedComponent(
                id="c-1",
                name="API",
                description="Camada de entrada",
            )
        ],
        architectural_risks=[
            ArchitecturalRisk(
                id="r-1",
                title="Acoplamento",
                description="Ponto de atenção",
                severity="medium",
            )
        ],
        basic_recommendations=[
            BasicRecommendation(
                id="rec-1",
                title="Isolar módulos",
                description="Reduzir dependências",
            )
        ],
        tokens_used=7,
    )
    report_relative_name = local_files.relative_report_path(job_id)
    report_path = settings.reports_dir / report_relative_name
    report_path.write_text(report.model_dump_json(), encoding="utf-8")

    response = await async_client.patch(
        f"/internal/v1/analysis-jobs/{job_id}",
        json={"status": "PROCESSING"},
        headers=internal_headers,
    )
    assert response.status_code == 200, response.text

    response = await async_client.post(
        f"/internal/v1/analysis-jobs/{job_id}/completion",
        json={
            "report_storage_path": report_relative_name,
            "tokens_used": 7,
            "report_schema_version": 1,
        },
        headers=internal_headers,
    )
    assert response.status_code == 200, response.text

    response = await async_client.get(
        f"/v1/analysis-jobs/{job_id}/report",
        headers=auth,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    reparsed = TechnicalReportV1.model_validate(payload)
    assert reparsed.identified_components[0].id == "c-1"
    assert reparsed.tokens_used == 7

    response = await async_client.get("/v1/clients/me/token-balance", headers=auth)
    assert response.status_code == 200
    assert response.json()["token_balance"] == 993  # 1000 - 7
