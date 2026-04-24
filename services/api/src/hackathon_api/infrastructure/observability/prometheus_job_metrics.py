from hackathon_api.application.ports import JobMetricsPort
from hackathon_api.infrastructure.observability import metrics as prom


class PrometheusJobMetrics(JobMetricsPort):
    def increment_status_label(self, status: str) -> None:
        prom.analysis_jobs_total.labels(status).inc()

    def add_upload_bytes(self, byte_count: int) -> None:
        prom.diagram_upload_bytes_total.inc(byte_count)

    def add_tokens_consumed(self, client_id: str, token_count: int) -> None:
        prom.ai_tokens_consumed_total.labels(client_id).inc(token_count)
