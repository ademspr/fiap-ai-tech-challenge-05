from hackathon_api.application.ports import HttpRequestMetricsPort
from hackathon_api.infrastructure.observability import metrics as prom


class PrometheusHttpRequestMetrics(HttpRequestMetricsPort):
    def record_http_request(
        self,
        method: str,
        path_group: str,
        endpoint: str,
        status_code: int,
        elapsed_seconds: float,
    ) -> None:
        prom.http_request_latency_seconds.labels(method, path_group, endpoint).observe(
            elapsed_seconds
        )
        prom.http_responses_total.labels(
            method, path_group, endpoint, str(status_code)
        ).inc()
