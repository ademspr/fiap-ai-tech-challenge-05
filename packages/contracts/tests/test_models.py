import pytest
from pydantic import ValidationError

from hackathon_contracts import (
    DEFAULT_DIAGRAM_QUEUE_NAME,
    DIAGRAM_EXCHANGE_NAME,
    DIAGRAM_ROUTING_KEY_ANALYZE,
    JobCompletionV1,
    TechnicalReportV1,
)


def test_technical_report_v1_minimal_json_roundtrip():
    raw = '{"schema_version": 1}'
    m = TechnicalReportV1.model_validate_json(raw)
    assert m.schema_version == 1
    assert m.identified_components == []


def test_technical_report_v1_invalid_nested_rejected():
    raw = '{"schema_version": 1, "identified_components": [{}]}'
    with pytest.raises(ValidationError):
        TechnicalReportV1.model_validate_json(raw)


def test_messaging_topology_constants():
    assert DIAGRAM_EXCHANGE_NAME == "hackathon.diagrams"
    assert DIAGRAM_ROUTING_KEY_ANALYZE == "analyze"
    assert DEFAULT_DIAGRAM_QUEUE_NAME == "diagram.analysis"


def test_job_completion_v1_rejects_negative_tokens():
    with pytest.raises(ValidationError):
        JobCompletionV1(
            report_storage_path="x.json",
            tokens_used=-1,
            report_schema_version=1,
        )
