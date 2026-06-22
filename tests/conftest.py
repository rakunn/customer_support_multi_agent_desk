import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def default_to_local_runtime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_RUNTIME", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
