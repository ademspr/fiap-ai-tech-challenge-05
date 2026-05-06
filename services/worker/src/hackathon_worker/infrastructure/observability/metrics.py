from prometheus_client import Counter, start_http_server

worker_state_transitions_total = Counter(
    "worker_state_transitions_total",
    "Worker FSM transitions",
    ["to_phase"],
)

diagram_jobs_processed_total = Counter(
    "diagram_jobs_processed_total",
    "Diagram jobs finished by outcome",
    ["outcome"],
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
