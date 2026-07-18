"""
Atlas AI – application configuration.

All settings are read from environment variables (or a .env file).
Pydantic-Settings validates and coerces every value at startup so that
misconfiguration surfaces immediately rather than at runtime.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object – a single source of truth for all config."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "Atlas AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------
    # HTTP server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ------------------------------------------------------------------
    # Database (PostgreSQL + pgvector)
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://atlas:atlas@localhost:5432/atlasdb",
        description="Async SQLAlchemy connection string (asyncpg driver).",
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL used for caching and pub/sub.",
    )
    REDIS_MAX_CONNECTIONS: int = 50

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key.")
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.2

    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------
    GITHUB_TOKEN: str = Field(default="", description="GitHub personal access token.")
    GITHUB_ORG: str = Field(default="", description="Default GitHub organisation.")
    GITHUB_REPO: str = Field(default="", description="Default GitHub repository (owner/repo).")

    # ------------------------------------------------------------------
    # Jira
    # ------------------------------------------------------------------
    JIRA_URL: AnyHttpUrl = Field(
        default="https://example.atlassian.net",  # type: ignore[assignment]
        description="Jira base URL.",
    )
    JIRA_EMAIL: str = Field(default="", description="Jira account e-mail.")
    JIRA_API_TOKEN: str = Field(default="", description="Jira API token.")
    JIRA_PROJECT_KEY: str = Field(default="OPS", description="Jira project key for incidents.")

    # ------------------------------------------------------------------
    # Slack
    # ------------------------------------------------------------------
    SLACK_BOT_TOKEN: str = Field(default="", description="Slack bot OAuth token (xoxb-).")
    SLACK_SIGNING_SECRET: str = Field(default="", description="Slack signing secret.")
    SLACK_INCIDENT_CHANNEL: str = Field(
        default="#incidents", description="Default Slack channel for incident alerts."
    )

    # ------------------------------------------------------------------
    # Kubernetes
    # ------------------------------------------------------------------
    KUBERNETES_CONTEXT: str = Field(
        default="", description="kubectl context to use. Empty = in-cluster."
    )
    KUBERNETES_NAMESPACE: str = Field(
        default="default", description="Default namespace for queries."
    )
    KUBECONFIG_PATH: str = Field(default="~/.kube/config", description="Path to kubeconfig.")

    # ------------------------------------------------------------------
    # Prometheus
    # ------------------------------------------------------------------
    PROMETHEUS_URL: AnyHttpUrl = Field(
        default="http://prometheus:9090",  # type: ignore[assignment]
        description="Prometheus HTTP API base URL.",
    )

    # ------------------------------------------------------------------
    # Confluence / Documentation
    # ------------------------------------------------------------------
    CONFLUENCE_URL: AnyHttpUrl = Field(
        default="https://example.atlassian.net/wiki",  # type: ignore[assignment]
        description="Confluence base URL.",
    )
    CONFLUENCE_USERNAME: str = ""
    CONFLUENCE_API_TOKEN: str = ""
    CONFLUENCE_SPACE_KEY: str = "OPS"

    # ------------------------------------------------------------------
    # Ceph / Storage
    # ------------------------------------------------------------------
    CEPH_DASHBOARD_URL: AnyHttpUrl = Field(
        default="http://ceph-dashboard:8080",  # type: ignore[assignment]
    )
    CEPH_API_USER: str = ""
    CEPH_API_PASSWORD: str = ""

    # ------------------------------------------------------------------
    # OpenTelemetry
    # ------------------------------------------------------------------
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "atlas-ai-backend"

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default="changeme-in-production-use-a-long-random-string",
        description="JWT signing key.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # Learning / Vector
    # ------------------------------------------------------------------
    VECTOR_SIMILARITY_THRESHOLD: float = 0.80
    LEARNING_AUTO_APPLY: bool = False

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def _warn_openai_key(cls, v: str) -> str:
        if not v:
            import warnings

            warnings.warn(
                "OPENAI_API_KEY is not set – AI agents will not work.",
                stacklevel=2,
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
