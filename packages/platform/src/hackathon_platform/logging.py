import logging
import sys

import structlog


def configure_logging(
    json_logs: bool = True,
    *,
    service_name: str | None = None,
) -> None:
    """Bootstrap structlog + stdlib for JSON or console output (API and worker)."""

    def _service_processor(
        _logger: object, _method_name: str, event_dict: dict[str, object]
    ) -> dict[str, object]:
        if service_name:
            event_dict["service"] = service_name
        return event_dict

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _service_processor,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_logs:
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
