from fastapi.testclient import TestClient
from pathlib import Path

from app.db.seed import demo_store
from app.main import app


def setup_function() -> None:
    demo_store.reset()


def test_root_serves_support_desk_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Customer Support Agent Desk" in response.text
    assert "Approval Queue" in response.text


def test_root_uses_dynamic_runtime_status_label() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="runtimeStatus"' in response.text
    assert "Local deterministic agents" not in response.text


def test_root_chat_starts_without_pretending_customer_sent_message() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert '<article class="message customer">' not in response.text
    assert ">I want a refund for order #1005. It arrived damaged.</textarea>" not in response.text


def test_root_system_message_suggests_quick_non_refund_examples() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert (
        "Send a message to see how the desk routes it, checks order details, "
        "handles approvals, and reviews the reply."
    ) in response.text
    assert "Where is my order #1003?" in response.text
    assert "What is your return policy for opened items?" in response.text
    assert "The CSV upload page crashes." in response.text
    assert "Please escalate this to a human." in response.text


def test_root_exposes_navigation_targets_for_approvals_and_evals() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'data-view="approvals"' in response.text
    assert 'data-view="evaluations"' in response.text
    assert 'id="evaluationPanel"' in response.text
    assert 'id="runEvals"' in response.text


def test_root_exposes_orders_and_database_admin_sections() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'data-view="orders"' in response.text
    assert 'data-view="database-admin"' in response.text
    assert 'id="createOrderForm"' in response.text
    assert 'id="databaseAdminPanel"' in response.text


def test_frontend_script_wires_navigation_and_eval_runner() -> None:
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert "setActiveView" in script
    assert "refreshRuntimeStatus" in script
    assert "/health" in script
    assert "/api/evals/run" in script
    assert "/api/orders" in script
    assert "/api/admin/reset" in script


def test_frontend_script_prevents_duplicate_chat_submits() -> None:
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert "sendButton.disabled = true" in script
    assert "messageInput.value = \"\"" in script
    assert "sendButton.disabled = false" in script


def test_frontend_script_uses_stable_chat_session_id() -> None:
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert "const chatSessionId = getChatSessionId();" in script
    assert "sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY)" in script
    assert "session_id: chatSessionId" in script
    assert "session_id: `ui_${Date.now()}`" not in script


def test_frontend_script_replaces_thinking_bubble_with_typed_agent_response() -> None:
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert "appendThinkingMessage" in script
    assert "setAttribute(\"aria-busy\", \"true\")" in script
    assert "const pendingAgentMessage = appendThinkingMessage();" in script
    assert "const minimumThinkingTime = wait(320);" in script
    assert "await minimumThinkingTime;" in script
    assert "await typeMessageText(pendingAgentMessage, response.agent, response.message);" in script
    assert 'appendMessage("agent", response.agent, response.message)' not in script


def test_frontend_styles_render_accessible_thinking_state() -> None:
    styles = Path("frontend/styles.css").read_text(encoding="utf-8")

    assert ".message.pending" in styles
    assert ".thinking-copy" in styles
    assert ".thinking-dot" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


def test_ticket_and_trace_endpoints_return_chat_state() -> None:
    client = TestClient(app)
    client.post(
        "/api/chat",
        json={
            "session_id": "session_ui",
            "customer_email": "maya@example.com",
            "message": "Where is my order #1003?",
        },
    )

    tickets = client.get("/api/tickets")
    traces = client.get("/api/traces")

    assert tickets.status_code == 200
    assert traces.status_code == 200
    assert tickets.json()[0]["intent"] == "order_status"
    assert traces.json()[0]["agent_name"] == "Triage Agent"
