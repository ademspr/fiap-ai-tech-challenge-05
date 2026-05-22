"""Real LLM-based architecture diagram analysis using Ollama (OpenAI-compatible API)."""

import base64
import json
import time

import structlog
from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from hackathon_contracts import (
    ArchitecturalRisk,
    BasicRecommendation,
    IdentifiedComponent,
    TechnicalReportV1,
)
from hackathon_worker.application.prompt_builder import build_system_prompt, build_user_prompt
from hackathon_worker.application.pdf_converter import pdf_to_png_bytes

log = structlog.get_logger(__name__)

_FALLBACK_REPORT = TechnicalReportV1(
    schema_version=1,
    analysis_summary="Automated analysis could not produce a structured result. Manual review required.",
    identified_components=[
        IdentifiedComponent(
            id="cmp-fallback",
            name="Unknown",
            description="Model output could not be parsed. Please review the diagram manually.",
        )
    ],
    architectural_risks=[
        ArchitecturalRisk(
            id="risk-fallback",
            title="Analysis failure",
            description="The AI model returned an unstructured or invalid response.",
            severity="high",
        )
    ],
    basic_recommendations=[
        BasicRecommendation(
            id="rec-fallback",
            title="Retry analysis",
            description="Re-submit the diagram or review it manually with a software architect.",
        )
    ],
    tokens_used=0,
    model_metadata={"engine": "fallback"},
)


def _diagram_to_images(diagram_bytes: bytes, content_type: str) -> list[bytes]:
    """Return a list of PNG image bytes from the diagram (handles PDF multi-page)."""
    if content_type == "application/pdf":
        return pdf_to_png_bytes(diagram_bytes, max_pages=3)
    return [diagram_bytes]


def _build_image_messages(images: list[bytes]) -> list[dict]:
    """Build the image content items for the OpenAI messages API."""
    items: list[dict] = []
    for img_bytes in images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        items.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            }
        )
    return items


def _parse_report(raw_text: str, model_name: str, tokens_used: int) -> TechnicalReportV1:
    """Parse the LLM JSON output into a TechnicalReportV1, raising on invalid schema."""
    try:
        data = json.loads(raw_text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON output: {raw_text[:200]}") from exc

    data.setdefault("schema_version", 1)
    data["tokens_used"] = tokens_used
    data.setdefault("model_metadata", {})
    data["model_metadata"]["engine"] = model_name

    return TechnicalReportV1.model_validate(data)


def run_real_analysis(
    diagram_bytes: bytes,
    content_type: str,
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout: int,
    max_retries: int,
) -> tuple[TechnicalReportV1, int]:
    """Analyse a diagram using the configured LLM provider.

    Returns:
        Tuple of (TechnicalReportV1, tokens_used).
        On unrecoverable LLM error, returns a fallback report with tokens_used=0.
    """
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    images = _diagram_to_images(diagram_bytes, content_type)
    image_items = _build_image_messages(images)

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_user_prompt(content_hint=content_type)},
                *image_items,
            ],
        },
    ]

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.2,
            )

            raw = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            log.info(
                "llm_response_received",
                model=model,
                tokens_used=tokens_used,
                attempt=attempt,
            )

            report = _parse_report(raw, model_name=model, tokens_used=tokens_used)
            report = report.model_copy(update={"tokens_used": tokens_used})
            return report, tokens_used

        except RateLimitError as exc:
            last_error = exc
            wait = 2 ** attempt
            log.warning("llm_rate_limited", attempt=attempt, wait_seconds=wait)
            time.sleep(wait)

        except APITimeoutError as exc:
            last_error = exc
            log.warning("llm_timeout", attempt=attempt, timeout=timeout)

        except (ValidationError, ValueError) as exc:
            last_error = exc
            log.warning("llm_invalid_output", attempt=attempt, error=str(exc))

        except APIError as exc:
            last_error = exc
            log.warning("llm_api_error", attempt=attempt, error=str(exc))

    log.error(
        "llm_all_retries_failed",
        model=model,
        attempts=max_retries + 1,
        last_error=str(last_error),
    )
    fallback = _FALLBACK_REPORT.model_copy(
        update={"model_metadata": {"engine": model, "fallback": "true"}}
    )
    return fallback, 0
