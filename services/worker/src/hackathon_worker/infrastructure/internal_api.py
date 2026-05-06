from uuid import UUID

import httpx

from hackathon_contracts import JobCompletionV1, JobPatchV1
from hackathon_worker.config import settings

from hackathon_worker.application.ports import WorkerInternalApiPort


class InternalApiClient(WorkerInternalApiPort):
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._headers = {"X-Internal-Token": settings.internal_token}

    async def patch_job(self, job_id: UUID, body: JobPatchV1) -> None:
        url = f"{settings.internal_api_base.rstrip('/')}/internal/v1/analysis-jobs/{job_id}"
        response = await self._http.patch(
            url,
            json=body.model_dump(mode="json", exclude_none=True),
            headers=self._headers,
        )
        response.raise_for_status()

    async def complete_job(self, job_id: UUID, body: JobCompletionV1) -> None:
        url = (
            f"{settings.internal_api_base.rstrip('/')}/internal/v1/"
            f"analysis-jobs/{job_id}/completion"
        )
        response = await self._http.post(
            url,
            json=body.model_dump(mode="json", exclude_none=True),
            headers=self._headers,
        )
        response.raise_for_status()
