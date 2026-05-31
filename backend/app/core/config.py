from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "CEF Filter Proxy"
    APP_ENV: str = "development"
    DEBUG: bool = True

    LOG_LEVEL: str = "DEBUG"
    LOG_JSON: bool = False
    LOG_PER_EVENT: bool = True

    LISTEN_HOST: str = "0.0.0.0"  # noqa: S104  # nosec B104 - syslog receivers bind all ifaces by design
    LISTEN_PORT: int = 5514
    MAX_DATAGRAM_BYTES: int = 65535
    INGRESS_QUEUE_MAXSIZE: int = 10000
    WORKER_COUNT: int = 4

    ELK_HOST: str = "127.0.0.1"
    ELK_PORT: int = 5140

    DEFAULT_POLICY: str = Field(default="forward", pattern="^(forward|drop)$")
    FORWARD_ON_PARSE_ERROR: bool = True
    SEED_RULES_PATH: str = "config/rules.example.yaml"

    DATABASE_URL: str = "postgresql+asyncpg://cef:cef@localhost:5432/cef"
    DB_ECHO: bool = False
    DB_AUTO_CREATE: bool = True
    DB_POOL_SIZE: int = 5
    EVENT_PERSIST: bool = True
    EVENT_WRITE_QUEUE_MAXSIZE: int = 10000
    EVENT_WRITE_BATCH: int = 100

    API_HOST: str = "0.0.0.0"  # noqa: S104  # nosec B104 - bind-all; restrict via deployment/firewall
    API_PORT: int = 8080
    API_TOKEN: str | None = None
    CORS_ALLOW_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    EVENT_BUFFER_SIZE: int = 500

    ALLOWED_SOURCE_CIDRS: list[str] = Field(default_factory=list)
    RATE_LIMIT_PER_SOURCE_PER_SEC: int = 0

    @field_validator("API_TOKEN")
    @classmethod
    def _blank_token_is_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() in {"production", "prod"}


settings = Settings()
