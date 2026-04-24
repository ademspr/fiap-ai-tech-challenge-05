from pathlib import Path

from hackathon_contracts import DEFAULT_DIAGRAM_QUEUE_NAME
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/api_db"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    internal_token: str = "change-me-internal"
    uploads_dir: Path = Path("/data/uploads")
    reports_dir: Path = Path("/data/reports")
    min_tokens_estimate: int = 10
    max_upload_bytes: int = 25 * 1024 * 1024
    rabbitmq_queue_name: str = DEFAULT_DIAGRAM_QUEUE_NAME


settings = Settings()
