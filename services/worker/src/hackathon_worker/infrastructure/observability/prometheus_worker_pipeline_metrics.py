from hackathon_worker.application.ports import WorkerPipelineMetricsPort
from hackathon_worker.infrastructure.observability import metrics as prom


class PrometheusWorkerPipelineMetrics(WorkerPipelineMetricsPort):
    def record_state_transition(self, to_phase: str) -> None:
        prom.worker_state_transitions_total.labels(to_phase).inc()

    def record_diagram_processed(self, outcome: str) -> None:
        prom.diagram_jobs_processed_total.labels(outcome).inc()
