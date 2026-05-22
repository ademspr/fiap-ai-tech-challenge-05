"""Tests for the AI analyzer module with mocked OpenAI client."""

import json
from unittest.mock import MagicMock, patch

import pytest

from hackathon_contracts import TechnicalReportV1
from hackathon_worker.application.ai_analyzer import _parse_report, run_real_analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_usage(total_tokens: int) -> MagicMock:
    usage = MagicMock()
    usage.total_tokens = total_tokens
    return usage


def _make_response(content: str, total_tokens: int = 100) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    response.usage = _make_usage(total_tokens)
    return response


def _valid_report_json(tokens: int = 0) -> str:
    return json.dumps({
        "schema_version": 1,
        "analysis_summary": "System uses microservices.",
        "identified_components": [
            {"id": "cmp-1", "name": "API Gateway", "description": "Entry point."}
        ],
        "architectural_risks": [
            {"id": "risk-1", "title": "SPOF", "description": "Single instance.", "severity": "high"}
        ],
        "basic_recommendations": [
            {"id": "rec-1", "title": "Add replicas", "description": "Scale out."}
        ],
        "tokens_used": tokens,
    })


# ---------------------------------------------------------------------------
# _parse_report unit tests
# ---------------------------------------------------------------------------

def test_parse_report_valid_json():
    raw = _valid_report_json(tokens=50)
    report = _parse_report(raw, model_name="gemma4", tokens_used=99)
    assert isinstance(report, TechnicalReportV1)
    assert report.tokens_used == 99
    assert report.model_metadata["engine"] == "gemma4"
    assert report.analysis_summary == "System uses microservices."
    assert len(report.identified_components) == 1


def test_parse_report_invalid_json_raises():
    with pytest.raises(ValueError, match="non-JSON"):
        _parse_report("not json {{{", model_name="gemma4", tokens_used=0)


def test_parse_report_schema_mismatch_raises():
    # identified_components must have required fields
    bad = json.dumps({
        "identified_components": [{"id": "c1"}]  # missing name and description
    })
    with pytest.raises(Exception):  # ValidationError from Pydantic
        _parse_report(bad, model_name="gemma4", tokens_used=0)


# ---------------------------------------------------------------------------
# run_real_analysis integration (mocked OpenAI client)
# ---------------------------------------------------------------------------

def test_run_real_analysis_success():
    valid_json = _valid_report_json()
    fake_response = _make_response(valid_json, total_tokens=150)

    with patch("hackathon_worker.application.ai_analyzer.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = fake_response

        report, tokens_used = run_real_analysis(
            b"fake-image-bytes",
            "image/png",
            base_url="http://localhost:11434/v1",
            model="gemma4",
            api_key="ollama",
            timeout=30,
            max_retries=0,
        )

    assert tokens_used == 150
    assert report.tokens_used == 150
    assert report.analysis_summary == "System uses microservices."
    assert len(report.identified_components) == 1


def test_run_real_analysis_returns_fallback_on_json_error():
    fake_response = _make_response("This is not JSON at all.", total_tokens=10)

    with patch("hackathon_worker.application.ai_analyzer.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = fake_response

        report, tokens_used = run_real_analysis(
            b"fake-image-bytes",
            "image/png",
            base_url="http://localhost:11434/v1",
            model="gemma4",
            api_key="ollama",
            timeout=30,
            max_retries=0,
        )

    assert tokens_used == 0  # fallback returns 0
    assert report.model_metadata is not None
    assert report.model_metadata.get("fallback") == "true"


def test_run_real_analysis_retries_on_rate_limit():
    from openai import RateLimitError

    valid_json = _valid_report_json()
    success_response = _make_response(valid_json, total_tokens=200)

    rate_limit_exc = RateLimitError(
        message="rate limit",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )

    with patch("hackathon_worker.application.ai_analyzer.OpenAI") as MockClient, \
         patch("hackathon_worker.application.ai_analyzer.time.sleep"):
        instance = MockClient.return_value
        # First call raises, second succeeds
        instance.chat.completions.create.side_effect = [rate_limit_exc, success_response]

        report, tokens_used = run_real_analysis(
            b"fake-image-bytes",
            "image/png",
            base_url="http://localhost:11434/v1",
            model="gemma4",
            api_key="ollama",
            timeout=30,
            max_retries=1,
        )

    assert tokens_used == 200
    assert instance.chat.completions.create.call_count == 2


def test_run_real_analysis_tokens_used_from_response():
    valid_json = _valid_report_json()
    fake_response = _make_response(valid_json, total_tokens=999)

    with patch("hackathon_worker.application.ai_analyzer.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = fake_response

        report, tokens_used = run_real_analysis(
            b"fake-image-bytes",
            "image/jpeg",
            base_url="http://localhost:11434/v1",
            model="gemma4",
            api_key="ollama",
            timeout=30,
            max_retries=0,
        )

    assert tokens_used == 999
    assert report.tokens_used == 999


def test_run_real_analysis_pdf_triggers_converter():
    valid_json = _valid_report_json()
    fake_response = _make_response(valid_json, total_tokens=50)

    with patch("hackathon_worker.application.ai_analyzer.OpenAI") as MockClient, \
         patch("hackathon_worker.application.ai_analyzer.pdf_to_png_bytes") as mock_pdf:
        mock_pdf.return_value = [b"fake-png-bytes"]
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = fake_response

        run_real_analysis(
            b"fake-pdf-bytes",
            "application/pdf",
            base_url="http://localhost:11434/v1",
            model="gemma4",
            api_key="ollama",
            timeout=30,
            max_retries=0,
        )

    mock_pdf.assert_called_once_with(b"fake-pdf-bytes", max_pages=3)
