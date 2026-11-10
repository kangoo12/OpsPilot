from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: Literal["qwen3.5:9b"] = "qwen3.5:9b"
    ollama_timeout_seconds: float = Field(default=5, gt=0, le=30)
    classification_timeout_seconds: float = Field(default=120, ge=10, le=300)
    database_path: Path = Path("data/opspilot.db")

    @field_validator("ollama_base_url")
    @classmethod
    def require_local_ollama(cls, value: str) -> str:
        url = urlsplit(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("OLLAMA_BASE_URL must be an HTTP loopback URL without a path")
        _ = url.port  # Validate the port before making any requests.
        return value.rstrip("/")

    @field_validator("database_path")
    @classmethod
    def resolve_database_path(cls, value: Path) -> Path:
        resolved = (PROJECT_ROOT / value).resolve()
        if not resolved.is_relative_to(PROJECT_ROOT):
            raise ValueError("DATABASE_PATH must stay inside the OpsPilot repository")
        return resolved
