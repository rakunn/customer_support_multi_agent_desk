from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    openai_api_key: str
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
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./support_desk.db"),
        vector_db_dir=Path(os.getenv("VECTOR_DB_DIR", "./.vector_db")),
        app_env=os.getenv("APP_ENV", "development"),
        refund_auto_approval_limit=float(os.getenv("REFUND_AUTO_APPROVAL_LIMIT", "50.00")),
        enable_mock_refunds=_env_bool("ENABLE_MOCK_REFUNDS", True),
        enable_agent_tracing=_env_bool("ENABLE_AGENT_TRACING", True),
    )
