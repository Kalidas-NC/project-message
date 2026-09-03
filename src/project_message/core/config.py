"""Load settings from the environment and repo-root `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"

_STR_FIELDS = (
    "whatsapp_verify_token",
    "whatsapp_app_secret",
    "whatsapp_access_token",
    "whatsapp_phone_number_id",
    "whatsapp_waba_id",
    "gemini_api_key",
    "gemini_model",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_waba_id: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    inbound_debounce_seconds: float = 2

    @field_validator(*_STR_FIELDS, mode="before")
    @classmethod
    def strip_str(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    def can_send(self) -> bool:
        return bool(self.whatsapp_access_token and self.whatsapp_phone_number_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
