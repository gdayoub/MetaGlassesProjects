import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_token: SecretStr
    data_dir: Path = PROJECT_ROOT / "data"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_enabled: bool = False
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_enabled: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:4b"
    ollama_context_length: int = Field(default=4096, ge=2048, le=32768)
    timeout_seconds: float = Field(default=45, ge=1, le=120)
    max_output_tokens: int = Field(default=768, ge=64, le=4096)
    daily_request_limit: int = Field(default=100, ge=1, le=10000)
    requests_per_minute: int = Field(default=10, ge=1, le=120)
    retention_days: int = Field(default=7, ge=1, le=365)
    max_image_bytes: int = 5 * 1024 * 1024
    max_image_pixels: int = 20_000_000
    max_text_length: int = 4000
    max_history_chars: int = 16000
    max_history_messages: int = 12
    allowed_hosts: list[str] = ["127.0.0.1", "localhost", "[::1]", "testserver"]

    @field_validator("api_token")
    @classmethod
    def strong_token(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("LENSAGENT_API_TOKEN must contain at least 32 characters")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def local_ollama(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use a local HTTP loopback address without a path")
        return value.rstrip("/")

    @classmethod
    def from_env(cls) -> "Settings":
        values = {**dotenv_values(PROJECT_ROOT / ".env"), **os.environ}
        mapping = {
            "api_token": "LENSAGENT_API_TOKEN",
            "data_dir": "LENSAGENT_DATA_DIR",
            "gemini_api_key": "GEMINI_API_KEY",
            "gemini_model": "GEMINI_MODEL",
            "gemini_enabled": "GEMINI_ENABLED",
            "ollama_enabled": "OLLAMA_ENABLED",
            "ollama_base_url": "OLLAMA_BASE_URL",
            "ollama_model": "OLLAMA_MODEL",
            "ollama_context_length": "OLLAMA_CONTEXT_LENGTH",
            "timeout_seconds": "LENSAGENT_TIMEOUT_SECONDS",
            "max_output_tokens": "LENSAGENT_MAX_OUTPUT_TOKENS",
            "daily_request_limit": "LENSAGENT_DAILY_REQUEST_LIMIT",
            "requests_per_minute": "LENSAGENT_REQUESTS_PER_MINUTE",
            "retention_days": "LENSAGENT_RETENTION_DAYS",
        }
        selected = {key: values[name] for key, name in mapping.items() if values.get(name)}
        if "data_dir" in selected:
            path = Path(str(selected["data_dir"]))
            selected["data_dir"] = str(path if path.is_absolute() else PROJECT_ROOT / path)
        settings = cls.model_validate(selected)
        if values.get("LENSAGENT_ALLOWED_HOSTS"):
            settings.allowed_hosts = [
                host.strip()
                for host in str(values["LENSAGENT_ALLOWED_HOSTS"]).split(",")
                if host.strip()
            ]
        return settings
