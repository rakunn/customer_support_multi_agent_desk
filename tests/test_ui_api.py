from fastapi.testclient import TestClient

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
