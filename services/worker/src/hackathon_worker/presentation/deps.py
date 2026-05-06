import httpx

from hackathon_worker.application.ports import (
    WorkerInternalApiPort,
    WorkerObjectStoragePort,
    WorkerPipelineMetricsPort,
)
from hackathon_worker.config import settings
from hackathon_worker.infrastructure.internal_api import InternalApiClient
from hackathon_worker.infrastructure.observability.metrics import start_metrics_server
from hackathon_worker.infrastructure.observability.prometheus_worker_pipeline_metrics import (
    PrometheusWorkerPipelineMetrics,
)
from hackathon_worker.infrastructure.storage.object_storage_adapter import (
    MinioObjectStorageAdapter,
)

_worker_pipeline_metrics = PrometheusWorkerPipelineMetrics()
_object_storage = MinioObjectStorageAdapter()


def get_internal_api_client(http: httpx.AsyncClient) -> WorkerInternalApiPort:
    return InternalApiClient(http)


def get_worker_pipeline_metrics() -> WorkerPipelineMetricsPort:
    return _worker_pipeline_metrics


def get_object_storage() -> WorkerObjectStoragePort:
    return _object_storage


def start_prometheus_scrape_server() -> None:
    start_metrics_server(settings.metrics_port)
