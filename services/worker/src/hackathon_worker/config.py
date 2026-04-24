from pathlib import Path

from hackathon_contracts import DEFAULT_DIAGRAM_QUEUE_NAME
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue_name: str = DEFAULT_DIAGRAM_QUEUE_NAME
    internal_api_base: str = "http://localhost:8081"
    internal_token: str = "change-me-internal"
    uploads_dir: Path = Path("/data/uploads")
    reports_dir: Path = Path("/data/reports")
    metrics_port: int = 9100


settings = Settings()
