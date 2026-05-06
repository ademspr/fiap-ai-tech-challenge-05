from uuid import UUID

from hackathon_contracts import DIAGRAM_ROUTING_KEY_ANALYZE, AnalyzeDiagramJobV1

from hackathon_api.domain.exceptions import MessagingFailedError
from hackathon_api.infrastructure.messaging.bus import MessagePublisher


class RabbitAnalyzeJobPublisher:
    """Maps the domain publish intent to the concrete broker message and routing key."""

    def __init__(self, message_publisher: MessagePublisher) -> None:
        self._publisher = message_publisher

    async def publish(self, job_id: UUID, diagram_storage_path: str) -> None:
        queue_message = AnalyzeDiagramJobV1(
            job_id=str(job_id),
            schema_version=1,
            diagram_storage_path=diagram_storage_path,
        )
        try:
            await self._publisher.publish_json(
                DIAGRAM_ROUTING_KEY_ANALYZE, queue_message.model_dump_json().encode("utf-8")
            )
        except MessagingFailedError:
            raise
        except Exception as error:  # noqa: BLE001
            raise MessagingFailedError from error
