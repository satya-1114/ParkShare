from functools import lru_cache
from typing import List

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "ParkShare API"
    APP_VERSION: str = "0.3.0"
    DEBUG: bool = False

    SECRET_KEY: str = Field(default="dev-insecure-secret-change-me", min_length=16)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    JWT_ALGORITHM: str = "HS256"

    DATABASE_URL: str = "postgresql+asyncpg://parkshare:parkshare@localhost:5432/parkshare"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8080"]

    UPLOAD_DIRECTORY: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024

    API_V1_PREFIX: str = "/api/v1"

    # IBM watsonx.ai
    WATSONX_API_KEY: SecretStr = SecretStr("")
    WATSONX_PROJECT_ID: str = ""
    # Region-specific ML endpoint. MUST match the region where the watsonx.ai
    # Runtime service / project is provisioned. This project runs in Frankfurt.
    WATSONX_URL: str = "https://eu-de.ml.cloud.ibm.com"
    WATSONX_MODEL_ID: str = "ibm/granite-4-h-small"
    WATSONX_TIMEOUT_SECONDS: int = 20
    WATSONX_MAX_NEW_TOKENS: int = 512

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
