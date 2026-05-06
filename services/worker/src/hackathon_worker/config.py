from hackathon_contracts import DEFAULT_DIAGRAM_QUEUE_NAME
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


settings = Settings()
