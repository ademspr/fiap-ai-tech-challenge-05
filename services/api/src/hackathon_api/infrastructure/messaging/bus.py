from abc import ABC, abstractmethod


class MessagePublisher(ABC):
    @abstractmethod
    async def publish_json(self, routing_key: str, body: bytes) -> None:
        pass


class NoOpMessagePublisher(MessagePublisher):
    async def publish_json(self, routing_key: str, body: bytes) -> None:
        _ = routing_key, body
