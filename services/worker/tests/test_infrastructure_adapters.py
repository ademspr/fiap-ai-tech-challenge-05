"""Unit tests for thin infrastructure adapters (no external I/O)."""
from unittest.mock import MagicMock, patch

from hackathon_worker.infrastructure.observability.prometheus_worker_pipeline_metrics import (
    PrometheusWorkerPipelineMetrics,
)
from hackathon_worker.infrastructure.storage.object_storage_adapter import (
    MinioObjectStorageAdapter,
)


# ---------------------------------------------------------------------------
# PrometheusWorkerPipelineMetrics
# ---------------------------------------------------------------------------


def test_record_state_transition_increments_counter():
    metrics = PrometheusWorkerPipelineMetrics()
    with patch(
        "hackathon_worker.infrastructure.observability.prometheus_worker_pipeline_metrics.prom"
    ) as mock_prom:
        mock_counter = MagicMock()
        mock_prom.worker_state_transitions_total = mock_counter
        metrics.record_state_transition("PROCESSING")
        mock_counter.labels.assert_called_once_with("PROCESSING")
        mock_counter.labels.return_value.inc.assert_called_once()


def test_record_diagram_processed_increments_counter():
    metrics = PrometheusWorkerPipelineMetrics()
    with patch(
        "hackathon_worker.infrastructure.observability.prometheus_worker_pipeline_metrics.prom"
    ) as mock_prom:
        mock_counter = MagicMock()
        mock_prom.diagram_jobs_processed_total = mock_counter
        metrics.record_diagram_processed("success")
        mock_counter.labels.assert_called_once_with("success")
        mock_counter.labels.return_value.inc.assert_called_once()


# ---------------------------------------------------------------------------
# MinioObjectStorageAdapter
# ---------------------------------------------------------------------------


def test_read_diagram_bytes_delegates_to_blob_store():
    adapter = MinioObjectStorageAdapter()
    with patch(
        "hackathon_worker.infrastructure.storage.object_storage_adapter.blob_store"
    ) as mock_blob:
        mock_blob.read_diagram_bytes.return_value = b"img"
        result = adapter.read_diagram_bytes("job/diagram.png")
        mock_blob.read_diagram_bytes.assert_called_once_with("job/diagram.png")
        assert result == b"img"


def test_write_report_bytes_delegates_to_blob_store():
    adapter = MinioObjectStorageAdapter()
    with patch(
        "hackathon_worker.infrastructure.storage.object_storage_adapter.blob_store"
    ) as mock_blob:
        adapter.write_report_bytes("job.json", b"report")
        mock_blob.write_report_bytes.assert_called_once_with("job.json", b"report")
