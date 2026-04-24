from prometheus_client import Counter, Histogram

analysis_jobs_total = Counter(
    "analysis_jobs_total",
    "Analysis jobs by terminal or current status label",
    ["status"],
)

diagram_upload_bytes_total = Counter(
    "diagram_upload_bytes_total",
    "Bytes accepted for diagram uploads",
)

ai_tokens_consumed_total = Counter(
    "ai_tokens_consumed_total",
    "Tokens debited after successful analysis",
    ["client_id"],
)

http_request_latency_seconds = Histogram(
    "http_request_latency_seconds",
    "HTTP request latency",
    ["method", "path_group"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_responses_total = Counter(
    "http_responses_total",
    "HTTP responses by method, path group and status code",
    ["method", "path_group", "status"],
)
