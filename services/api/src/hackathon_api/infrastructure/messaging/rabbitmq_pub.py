import aio_pika
from hackathon_contracts import (
    DEFAULT_DIAGRAM_DLQ_QUEUE_NAME,
    DIAGRAM_DLQ_ROUTING_KEY,
    DIAGRAM_DLX_EXCHANGE_NAME,
    DIAGRAM_EXCHANGE_NAME,
    DIAGRAM_ROUTING_KEY_ANALYZE,
)

from hackathon_api.config import settings
from hackathon_api.infrastructure.messaging.bus import MessagePublisher


class RabbitMqPublisher(MessagePublisher):
    """Publishes to the same topology the worker consumes."""

    def __init__(self, channel: aio_pika.abc.AbstractChannel) -> None:
        self._channel = channel
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._ready = False

    async def ensure_topology(self) -> None:
        if self._ready:
            return
        dlx = await self._channel.declare_exchange(
            DIAGRAM_DLX_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
        )
        dlq = await self._channel.declare_queue(DEFAULT_DIAGRAM_DLQ_QUEUE_NAME, durable=True)
        await dlq.bind(dlx, routing_key=DIAGRAM_DLQ_ROUTING_KEY)

        self._exchange = await self._channel.declare_exchange(
            DIAGRAM_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await self._channel.declare_queue(
            settings.rabbitmq_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": DIAGRAM_DLX_EXCHANGE_NAME,
                "x-dead-letter-routing-key": DIAGRAM_DLQ_ROUTING_KEY,
            },
        )
        await queue.bind(self._exchange, routing_key=DIAGRAM_ROUTING_KEY_ANALYZE)
        self._ready = True

    async def publish_json(self, routing_key: str, body: bytes) -> None:
        await self.ensure_topology()
        assert self._exchange is not None
        await self._exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )


class _RabbitResource:
    def __init__(self) -> None:
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._connection: aio_pika.RobustConnection | None = None

    async def get_channel(self) -> aio_pika.abc.AbstractChannel:
        if self._channel is not None and not self._channel.is_closed:
            return self._channel

        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        return self._channel

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

        self._channel = None
        self._connection = None


_rabbit = _RabbitResource()


async def connect_rabbit() -> aio_pika.abc.AbstractChannel:
    return await _rabbit.get_channel()


async def close_rabbit() -> None:
    await _rabbit.close()
