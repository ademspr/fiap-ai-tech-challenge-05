from typing import Literal

from hackathon_contracts import DEFAULT_DIAGRAM_QUEUE_NAME
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue_name: str = DEFAULT_DIAGRAM_QUEUE_NAME
    internal_api_base: str = "http://localhost:8081"
    internal_token: str = "change-me-internal"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio12345"
    minio_bucket: str = "hackathon"
    minio_use_ssl: bool = False
    metrics_port: int = 9100

    # Ollama / AI settings
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "gemma4"
    ai_timeout_seconds: int = 120
    ai_max_retries: int = 2

    # Provider selection: "ollama" (local) or "cloud" (any OpenAI-compatible API)
    ai_provider: Literal["ollama", "cloud"] = "ollama"
    cloud_api_key: str = ""
    cloud_model: str = "google/gemma-4-31b-it:free"
    cloud_base_url: str = "https://openrouter.ai/api/v1"

    @computed_field
    @property
    def ai_base_url(self) -> str:
        return self.cloud_base_url if self.ai_provider == "cloud" else self.ollama_base_url

    @computed_field
    @property
    def ai_model(self) -> str:
        return self.cloud_model if self.ai_provider == "cloud" else self.ollama_model

    @computed_field
    @property
    def ai_api_key(self) -> str:
        return self.cloud_api_key if self.ai_provider == "cloud" else "ollama"


settings = Settings()
