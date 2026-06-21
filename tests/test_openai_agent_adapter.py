import asyncio
import os
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.db.seed import demo_store
from app.schemas.agent_outputs import ChatResponse, ToolError
from app.services import openai_agent_adapter
from app.services.agent_runner import run_support_turn_async


def setup_function() -> None:
    demo_store.reset()
    get_settings.cache_clear()


def teardown_function() -> None:
    get_settings.cache_clear()


def _enable_openai_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()


class FakeRunResult:
    def __init__(self, final_output: ChatResponse) -> None:
        self.final_output = final_output
        self.last_agent = SimpleNamespace(name=final_output.agent)
        self.new_items = [SimpleNamespace(type="tool_call_item", tool_name="lookup_order")]


def test_openai_runtime_converts_structured_sdk_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_openai_runtime(monkeypatch)

    async def fake_run(*args, **kwargs):
        assert kwargs["context"].customer_email == "maya@example.com"
        assert kwargs["run_config"].model == "gpt-test"
        return FakeRunResult(
            ChatResponse(
                ticket_id="ticket_123",
                agent="Refund Agent",
                intent="refund_request",
                status="pending_approval",
                message="I prepared a refund request for manager approval.",
                approval_request_id="approval_123",
                tool_calls=[],
            )
        )

    monkeypatch.setattr(openai_agent_adapter.Runner, "run", fake_run)

    response = asyncio.run(
        run_support_turn_async(
            session_id="session_openai",
            customer_email="maya@example.com",
            message="I want a refund for order #1005. It arrived damaged.",
        )
    )

    assert response.agent == "Refund Agent"
    assert response.status == "pending_approval"
    assert response.tool_calls == ["lookup_order"]
    events = demo_store.agent_events
    assert events[-1]["event_type"] == "openai_response"
    assert events[-1]["payload"]["last_agent"] == "Refund Agent"
    assert events[-1]["payload"]["tool_calls"] == ["lookup_order"]


def test_openai_runtime_applies_output_guardrails(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_openai_runtime(monkeypatch)

    async def fake_run(*args, **kwargs):
        return FakeRunResult(
            ChatResponse(
                ticket_id="ticket_123",
                agent="Refund Agent",
                intent="refund_request",
                status="pending_approval",
                message="Your refund has been issued and processed.",
                approval_request_id="approval_123",
                tool_calls=[],
            )
        )

    monkeypatch.setattr(openai_agent_adapter.Runner, "run", fake_run)

    response = asyncio.run(
        run_support_turn_async(
            session_id="session_guardrail",
            customer_email="maya@example.com",
            message="I want a refund for order #1005. It arrived damaged.",
        )
    )

    assert "pending human approval" in response.message
    assert "issued" not in response.message.lower()


def test_openai_runtime_returns_safe_error_without_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_openai_runtime(monkeypatch)

    async def fake_run(*args, **kwargs):
        raise RuntimeError("sdk unavailable")

    monkeypatch.setattr(openai_agent_adapter.Runner, "run", fake_run)

    response = asyncio.run(
        run_support_turn_async(
            session_id="session_failure",
            customer_email="maya@example.com",
            message="Where is order #1003?",
        )
    )

    assert response.agent == "OpenAI Runtime"
    assert response.intent == "runtime_error"
    assert response.status == "error"
    assert response.tool_calls == []
    assert "local" not in response.message.lower()
    assert demo_store.agent_events[-1]["event_type"] == "sdk_error"


def test_context_bound_refund_tool_blocks_another_customer_order() -> None:
    context = SimpleNamespace(
        context=openai_agent_adapter.OpenAISupportContext(
            session_id="session_tools",
            customer_email="jordan@example.com",
        )
    )

    result = openai_agent_adapter.create_refund_approval_request_for_model(
        context,
        order_id="1005",
        reason="It arrived damaged.",
        amount=129.99,
        ticket_id=None,
    )

    assert isinstance(result, ToolError)
    assert result.code == "order_customer_mismatch"
    assert demo_store.approvals == {}


def test_context_bound_refund_tool_reuses_duplicate_pending_approval() -> None:
    context = SimpleNamespace(
        context=openai_agent_adapter.OpenAISupportContext(
            session_id="session_tools",
            customer_email="maya@example.com",
        )
    )

    first = openai_agent_adapter.create_refund_approval_request_for_model(
        context,
        order_id="1005",
        reason="It arrived damaged.",
        amount=129.99,
        ticket_id=None,
    )
    second = openai_agent_adapter.create_refund_approval_request_for_model(
        context,
        order_id="1005",
        reason="It arrived damaged.",
        amount=129.99,
        ticket_id=None,
    )

    assert not isinstance(first, ToolError)
    assert not isinstance(second, ToolError)
    assert first.id == second.id
    assert len(demo_store.approvals) == 1


def test_context_bound_refund_tool_blocks_already_refunded_order() -> None:
    context = SimpleNamespace(
        context=openai_agent_adapter.OpenAISupportContext(
            session_id="session_tools",
            customer_email="maya@example.com",
        )
    )
    demo_store.mark_refunded("approval_existing", "1005")

    result = openai_agent_adapter.create_refund_approval_request_for_model(
        context,
        order_id="1005",
        reason="It arrived damaged.",
        amount=129.99,
        ticket_id=None,
    )

    assert isinstance(result, ToolError)
    assert result.code == "refund_already_processed"


def test_refund_agent_does_not_expose_refund_issuance_tool() -> None:
    support_agents = openai_agent_adapter.build_support_agents(model="gpt-test")

    tool_names = {tool.name for tool in support_agents.refund_agent.tools}

    assert "create_refund_approval_request" in tool_names
    assert "issue_mock_refund" not in tool_names


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_OPENAI_TESTS") != "true" or not os.getenv("OPENAI_API_KEY"),
    reason="live OpenAI smoke test requires RUN_LIVE_OPENAI_TESTS=true and OPENAI_API_KEY",
)
def test_live_openai_runtime_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME", "openai")
    get_settings.cache_clear()

    response = asyncio.run(
        run_support_turn_async(
            session_id="session_live_smoke",
            customer_email="maya@example.com",
            message="Where is order #1003?",
        )
    )

    assert response.message
    assert response.agent
