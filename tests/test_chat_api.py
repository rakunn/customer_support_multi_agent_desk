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


def test_refund_followup_uses_order_id_from_same_session_context() -> None:
    client = TestClient(app)
    session_id = "session_refund_context"

    first = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "customer_email": "maya@example.com",
            "message": "I want a refund of 1005# can you help with that?",
        },
    )
    second = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "customer_email": "maya@example.com",
            "message": "It arrived damaged",
        },
    )

    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["agent"] == "Refund Agent"
    assert first_payload["status"] == "needs_info"
    assert "reason" in first_payload["message"].lower()

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["agent"] == "Refund Agent"
    assert second_payload["intent"] == "refund_request"
    assert second_payload["status"] == "pending_approval"
    assert second_payload["approval_request_id"].startswith("approval_")
    assert "share your order" not in second_payload["message"].lower()
    assert "lookup_order" in second_payload["tool_calls"]
    assert len(demo_store.approvals) == 1


def test_refund_followup_does_not_reuse_context_across_sessions() -> None:
    client = TestClient(app)

    first = client.post(
        "/api/chat",
        json={
            "session_id": "session_refund_context_a",
            "customer_email": "maya@example.com",
            "message": "I want a refund of 1005# can you help with that?",
        },
    )
    second = client.post(
        "/api/chat",
        json={
            "session_id": "session_refund_context_b",
            "customer_email": "maya@example.com",
            "message": "It arrived damaged",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["status"] == "open"
    assert "share the order" in second_payload["message"].lower()
    assert demo_store.approvals == {}


def test_pending_refund_context_does_not_override_clear_new_order_status_request() -> None:
    client = TestClient(app)
    session_id = "session_refund_context_switch"

    first = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "customer_email": "maya@example.com",
            "message": "I want a refund of 1005# can you help with that?",
        },
    )
    second = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "customer_email": "maya@example.com",
            "message": "Where is order #1003?",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["agent"] == "Order Status Agent"
    assert second_payload["intent"] == "order_status"
    assert "In transit" in second_payload["message"]
    assert demo_store.approvals == {}
