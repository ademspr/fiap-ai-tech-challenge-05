import asyncio

import aio_pika
import httpx
import structlog

from hackathon_contracts import DIAGRAM_EXCHANGE_NAME, DIAGRAM_ROUTING_KEY_ANALYZE
from hackathon_platform import configure_logging

from hackathon_worker.application.execute_diagram_job import execute_diagram_job
from hackathon_worker.config import settings
from hackathon_worker.presentation.deps import (
    get_internal_api_client,
    get_worker_pipeline_metrics,
    start_prometheus_scrape_server,
)

log = structlog.get_logger(__name__)


async def consume_loop() -> None:
    configure_logging()
    start_prometheus_scrape_server()

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        DIAGRAM_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
    )
    queue = await channel.declare_queue(settings.rabbitmq_queue_name, durable=True)
    await queue.bind(exchange, routing_key=DIAGRAM_ROUTING_KEY_ANALYZE)

    log.info(
        "worker_ready",
        queue=settings.rabbitmq_queue_name,
        exchange=DIAGRAM_EXCHANGE_NAME,
    )

    async with httpx.AsyncClient(timeout=120.0) as http:
        api = get_internal_api_client(http)
        pipeline_metrics = get_worker_pipeline_metrics()
        async with queue.iterator() as it:
            async for message in it:
                async with message.process(requeue=False):
                    await execute_diagram_job(
                        message.body, api, pipeline_metrics
                    )


def main() -> None:
    asyncio.run(consume_loop())


if __name__ == "__main__":
    main()
