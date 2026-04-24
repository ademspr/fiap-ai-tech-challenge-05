import httpx

from hackathon_worker.application.ports import (
    WorkerInternalApiPort,
    WorkerPipelineMetricsPort,
)
from hackathon_worker.config import settings
from hackathon_worker.infrastructure.internal_api import InternalApiClient
from hackathon_worker.infrastructure.observability.metrics import start_metrics_server
from hackathon_worker.infrastructure.observability.prometheus_worker_pipeline_metrics import (
    PrometheusWorkerPipelineMetrics,
)

_worker_pipeline_metrics = PrometheusWorkerPipelineMetrics()


def get_internal_api_client(http: httpx.AsyncClient) -> WorkerInternalApiPort:
    return InternalApiClient(http)


def get_worker_pipeline_metrics() -> WorkerPipelineMetricsPort:
    return _worker_pipeline_metrics


def start_prometheus_scrape_server() -> None:
    start_metrics_server(settings.metrics_port)
