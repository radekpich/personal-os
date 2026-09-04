from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    cors_origins: str

    cookie_secure: bool
    access_cookie_name: str
    refresh_cookie_name: str
    csrf_cookie_name: str
    csrf_header_name: str

    rate_limit_login: str
    rate_limit_default: str

    environment: str

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
