"""Application configuration, loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default so the project runs with zero setup; Postgres in prod.
    database_url: str = "sqlite:///./rfq.db"

    # MUST be overridden in production via the JWT_SECRET env var.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Set to "production" on the deployed instance.
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise the host-provided URL to a driver SQLAlchemy understands.

        Render, Railway and Heroku all hand out `postgres://` or
        `postgresql://`, but SQLAlchemy 2.x needs an explicit driver. Fixing it
        here rather than in the dashboard means the deploy cannot break on a
        detail nobody remembers to set.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
