"""RabbitMQ topology shared by API publisher and worker consumer.

Runtime queue name remains configurable per service via Settings; this module
holds the integration contract for exchange, routing key, and documented default queue name.
"""

DIAGRAM_EXCHANGE_NAME = "hackathon.diagrams"
DIAGRAM_ROUTING_KEY_ANALYZE = "analyze"
DEFAULT_DIAGRAM_QUEUE_NAME = "diagram.analysis"
