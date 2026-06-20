from fastapi.testclient import TestClient

from app.db.seed import demo_store
from app.main import app


def setup_function() -> None:
    demo_store.reset()


def test_chat_refund_request_creates_pending_approval() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={
            "session_id": "session_123",
            "customer_email": "maya@example.com",
            "message": "I want a refund for order #1005. It arrived damaged.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent"] == "Refund Agent"
    assert payload["intent"] == "refund_request"
    assert payload["status"] == "pending_approval"
    assert payload["approval_request_id"].startswith("approval_")
    assert payload["tool_calls"] == [
        "lookup_customer",
        "lookup_order",
        "check_refund_eligibility",
        "create_ticket",
        "create_refund_approval_request",
        "update_ticket",
    ]
    assert "issued" not in payload["message"].lower()


def test_chat_order_status_uses_order_lookup() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={
            "session_id": "session_124",
            "customer_email": "maya@example.com",
            "message": "Where is order #1003?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent"] == "Order Status Agent"
    assert payload["intent"] == "order_status"
    assert payload["status"] == "open"
    assert "In transit" in payload["message"]
    assert "lookup_order" in payload["tool_calls"]

