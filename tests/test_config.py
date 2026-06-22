import pytest

from app.config import RuntimeConfigError, get_settings, validate_runtime_settings


def setup_function() -> None:
    get_settings.cache_clear()


def teardown_function() -> None:
    get_settings.cache_clear()


def test_agent_runtime_defaults_to_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENT_RUNTIME", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.agent_runtime == "local"
    assert settings.openai_model == "gpt-5.5"
    validate_runtime_settings(settings)


def test_settings_loads_local_dotenv_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "AGENT_RUNTIME=openai\nOPENAI_MODEL=gpt-5.4\nOPENAI_API_KEY=test-key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AGENT_RUNTIME", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.agent_runtime == "openai"
    assert settings.openai_model == "gpt-5.4"
    assert settings.openai_api_key == "test-key"


def test_agent_runtime_can_select_openai_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.agent_runtime == "openai"
    assert settings.openai_model == "gpt-5.4"
    validate_runtime_settings(settings)


def test_openai_runtime_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_RUNTIME", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeConfigError, match="OPENAI_API_KEY"):
        validate_runtime_settings(get_settings())
