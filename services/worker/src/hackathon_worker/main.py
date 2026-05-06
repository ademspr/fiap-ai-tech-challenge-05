import asyncio
import logging

import aio_pika
import httpx
import structlog

from hackathon_contracts import (
    DEFAULT_DIAGRAM_DLQ_QUEUE_NAME,
    DIAGRAM_DLQ_ROUTING_KEY,
    DIAGRAM_DLX_EXCHANGE_NAME,
    DIAGRAM_EXCHANGE_NAME,
    DIAGRAM_ROUTING_KEY_ANALYZE,
)
from hackathon_platform import configure_logging
from hackathon_platform.minio_io import ensure_bucket

from hackathon_worker.application.execute_diagram_job import execute_diagram_job
from hackathon_worker.config import settings
from hackathon_worker.infrastructure.storage.minio_client import minio_client_singleton
from hackathon_worker.presentation.deps import (
    get_internal_api_client,
    get_object_storage,
    get_worker_pipeline_metrics,
    start_prometheus_scrape_server,
)

log = structlog.get_logger(__name__)


async def consume_loop() -> None:
    configure_logging(json_logs=True, service_name="worker")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    ensure_bucket(minio_client_singleton(), settings.minio_bucket)
    start_prometheus_scrape_server()

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    dlx = await channel.declare_exchange(
        DIAGRAM_DLX_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
    )
    dlq = await channel.declare_queue(DEFAULT_DIAGRAM_DLQ_QUEUE_NAME, durable=True)
    await dlq.bind(dlx, routing_key=DIAGRAM_DLQ_ROUTING_KEY)

    exchange = await channel.declare_exchange(
        DIAGRAM_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
    )
    queue = await channel.declare_queue(
        settings.rabbitmq_queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DIAGRAM_DLX_EXCHANGE_NAME,
            "x-dead-letter-routing-key": DIAGRAM_DLQ_ROUTING_KEY,
        },
    )
    await queue.bind(exchange, routing_key=DIAGRAM_ROUTING_KEY_ANALYZE)

    log.info(
        "worker_ready",
        queue=settings.rabbitmq_queue_name,
        exchange=DIAGRAM_EXCHANGE_NAME,
        dlq=DEFAULT_DIAGRAM_DLQ_QUEUE_NAME,
    )

    async with httpx.AsyncClient(timeout=120.0) as http:
        api = get_internal_api_client(http)
        pipeline_metrics = get_worker_pipeline_metrics()
        storage = get_object_storage()
        async with queue.iterator() as q_iter:
            async for message in q_iter:
                try:
                    await execute_diagram_job(message.body, api, pipeline_metrics, storage)
                except Exception:
                    log.exception("diagram_job_handler_failed_dead_letter")
                    await message.reject(requeue=False)
                else:
                    await message.ack()


def main() -> None:
    asyncio.run(consume_loop())


if __name__ == "__main__":
    main()
