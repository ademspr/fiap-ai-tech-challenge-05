import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from hackathon_platform import configure_logging
from hackathon_platform.minio_io import ensure_bucket
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from hackathon_api.application.ports import HttpRequestMetricsPort
from hackathon_api.config import settings
from hackathon_api.infrastructure.messaging.bus import NoOpMessagePublisher
from hackathon_api.infrastructure.messaging.rabbitmq_pub import (
    RabbitMqPublisher,
    close_rabbit,
    connect_rabbit,
)
from hackathon_api.infrastructure.observability.http_path import split_path_group_and_endpoint
from hackathon_api.infrastructure.observability.prometheus_http_request_metrics import (
    PrometheusHttpRequestMetrics,
)
from hackathon_api.infrastructure.storage.minio_client import minio_client_singleton
from hackathon_api.presentation.internal_router import router as internal_router
from hackathon_api.presentation.public_router import router as public_router

log = structlog.get_logger(__name__)

Send = Callable[[dict], Awaitable[None]]


class PrometheusMetricsAsgiMiddleware:
    """Records HTTP status from the final ASGI response.start (covers auth errors, etc.)."""

    def __init__(
        self,
        app: Callable,
        http_metrics: HttpRequestMetricsPort,
    ) -> None:
        self.app = app
        self._http_metrics = http_metrics

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500
        start = time.perf_counter()
        path = scope.get("path") or "/"
        method = scope.get("method") or "GET"

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            group, endpoint = split_path_group_and_endpoint(path)
            elapsed = time.perf_counter() - start
            self._http_metrics.record_http_request(
                method, group, endpoint, status_code, elapsed
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(json_logs=True, service_name="api")
    ensure_bucket(minio_client_singleton(), settings.minio_bucket)

    try:
        channel = await connect_rabbit()
        rabbitmq_publisher = RabbitMqPublisher(channel)
        await rabbitmq_publisher.ensure_topology()
        app.state.message_publisher = rabbitmq_publisher
        log.info("rabbitmq_connected")
    except Exception as error:
        log.warning("rabbitmq_unavailable", error=str(error))
        app.state.message_publisher = NoOpMessagePublisher()

    yield

    await close_rabbit()
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(title="FIAP Secure Systems API", lifespan=lifespan)
    http_metrics: HttpRequestMetricsPort = PrometheusHttpRequestMetrics()
    app.add_middleware(PrometheusMetricsAsgiMiddleware, http_metrics=http_metrics)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics():
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    app.include_router(public_router, prefix="/v1")
    app.include_router(internal_router, prefix="/internal/v1")

    return app


app = create_app()
