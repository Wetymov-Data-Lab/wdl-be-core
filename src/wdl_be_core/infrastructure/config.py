from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------------------------------------------------------------------
    # App
    # ---------------------------------------------------------------------------

    APP_VERSION:     str = "0.1.0"
    PROJECT_NAME:    str = "WDL Core API"
    PROJECT_DESC:    str = "API системы визуализации связей баз данных"

    DEBUG:           str | bool = False

    CORS_DISABLE:    str | bool = False
    CORS_REGEX:      str = r"https://.*\.wdl\.ru"
    PROD_SERVER_URL: str | None = None

    # ---------------------------------------------------------------------------
    # PostgreSQL
    # ---------------------------------------------------------------------------

    POSTGRES_SERVER:               str | None = "localhost"
    POSTGRES_USER:                 str | None = "postgres"
    POSTGRES_PASSWORD:             str | None = "postgres"
    POSTGRES_DB:                   str | None = "postgres"
    POSTGRES_PORT:                 str | None = "5432"
    SQLALCHEMY_ASYNC_DATABASE_URI: str | None = None
    SQLALCHEMY_ECHO:               bool = False

    @model_validator(mode="after")
    def assemble_database_uri(self) -> "Settings":
        if not self.SQLALCHEMY_ASYNC_DATABASE_URI:
            self.SQLALCHEMY_ASYNC_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
