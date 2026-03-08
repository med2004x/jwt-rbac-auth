from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="jwt-rbac-auth", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    database_url: str = Field(alias="DATABASE_URL")
    migration_database_url: str = Field(alias="MIGRATION_DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    jwt_issuer: str = Field(alias="JWT_ISSUER")
    jwt_audience: str = Field(alias="JWT_AUDIENCE")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    access_token_ttl_seconds: int = Field(default=900, alias="ACCESS_TOKEN_TTL_SECONDS")
    refresh_token_ttl_seconds: int = Field(default=259200, alias="REFRESH_TOKEN_TTL_SECONDS")
    default_admin_email: str = Field(alias="DEFAULT_ADMIN_EMAIL")
    default_admin_password: str = Field(alias="DEFAULT_ADMIN_PASSWORD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

