import json
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict


def _parse_cors(v: Any) -> list[str]:
    """Parse CORS origins from a string (JSON array or comma-separated) or list."""
    if isinstance(v, list):
        return v
    if not isinstance(v, str):
        return list(v)
    v = v.strip()
    # Try valid JSON first: ["http://...","http://..."]
    try:
        result = json.loads(v)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    # Fallback: uv --env-file strips inner quotes → [http://...,http://...]
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [origin.strip() for origin in v.split(",") if origin.strip()]


class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Encryption (Fernet — for addon settings)
    fernet_key: str

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # App
    environment: str = "development"

    # Addons
    local_files_library_path: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        **kwargs: Any,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        class SafeEnvSource(EnvSettingsSource):
            """Handles CORS_ORIGINS regardless of how the shell quotes the JSON array."""
            def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
                if field_name == "cors_origins":
                    return _parse_cors(value)
                return super().decode_complex_value(field_name, field, value)

        return (init_settings, SafeEnvSource(settings_cls), dotenv_settings, *kwargs.values())


@lru_cache
def get_settings() -> Settings:
    return Settings()
