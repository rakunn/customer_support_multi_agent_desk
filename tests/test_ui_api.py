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
    assert "/api/evals/run" in script
    assert "/api/orders" in script
    assert "/api/admin/reset" in script


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
