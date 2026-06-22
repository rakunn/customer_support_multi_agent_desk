from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel


class RuntimeConfigError(ValueError):
    """Raised when a selected agent runtime is missing required configuration."""


class Settings(BaseModel):
    agent_runtime: Literal["local", "openai"]
    openai_api_key: str
    openai_model: str
    database_url: str
    vector_db_dir: Path
    app_env: str
    refund_auto_approval_limit: float
    enable_mock_refunds: bool
    enable_agent_tracing: bool


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    return Settings(
        agent_runtime=os.getenv("AGENT_RUNTIME", "local").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.5").strip() or "gpt-5.5",
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./support_desk.db"),
        vector_db_dir=Path(os.getenv("VECTOR_DB_DIR", "./.vector_db")),
        app_env=os.getenv("APP_ENV", "development"),
        refund_auto_approval_limit=float(os.getenv("REFUND_AUTO_APPROVAL_LIMIT", "50.00")),
        enable_mock_refunds=_env_bool("ENABLE_MOCK_REFUNDS", True),
        enable_agent_tracing=_env_bool("ENABLE_AGENT_TRACING", True),
    )


def validate_runtime_settings(settings: Settings) -> None:
    if settings.agent_runtime == "openai" and not settings.openai_api_key.strip():
        raise RuntimeConfigError(
            "AGENT_RUNTIME=openai requires OPENAI_API_KEY to be configured."
        )
