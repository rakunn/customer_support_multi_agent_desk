from fastapi.testclient import TestClient

from app.db.seed import demo_store
from app.main import app


def setup_function() -> None:
    demo_store.reset()


def _chat(client: TestClient, customer_email: str | None, message: str) -> dict:
    response = client.post(
        "/api/chat",
        json={
            "session_id": f"session_{abs(hash((customer_email, message))) % 100000}",
            "customer_email": customer_email,
            "message": message,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_duplicate_pending_refund_reuses_existing_approval() -> None:
    client = TestClient(app)

    first = _chat(client, "maya@example.com", "I want a refund for order #1005. It arrived damaged.")
    second = _chat(client, "maya@example.com", "I still need a refund for order #1005. It arrived damaged.")

    assert first["approval_request_id"] == second["approval_request_id"]
    assert second["status"] == "pending_approval"
    assert "already waiting" in second["message"].lower()
    assert len(demo_store.approvals) == 1


def test_processed_order_refund_blocks_later_refund_request() -> None:
    client = TestClient(app)
    first = _chat(client, "maya@example.com", "I want a refund for order #1005. It arrived damaged.")
    approve_response = client.post(f"/api/approvals/{first['approval_request_id']}/approve")
    assert approve_response.status_code == 200

    second = _chat(client, "maya@example.com", "I need another refund for order #1005. It arrived damaged again.")

    assert second["approval_request_id"] is None
    assert second["status"] == "resolved"
    assert "already been processed" in second["message"].lower()
    assert len(demo_store.approvals) == 1


def test_refund_request_for_another_customer_order_is_blocked() -> None:
    client = TestClient(app)

    response = _chat(client, "jordan@example.com", "I want a refund for order #1005. It arrived damaged.")

    assert response["approval_request_id"] is None
    assert response["status"] == "blocked"
    assert "current customer account" in response["message"].lower()
    assert demo_store.approvals == {}


def test_refund_request_requires_verified_customer() -> None:
    client = TestClient(app)

    response = _chat(client, "unknown@example.com", "I want a refund for order #1005. It arrived damaged.")

    assert response["approval_request_id"] is None
    assert response["status"] == "blocked"
    assert "verify the customer email" in response["message"].lower()
    assert demo_store.approvals == {}


def test_damaged_in_transit_order_escalates_without_refund_approval() -> None:
    client = TestClient(app)

    response = _chat(client, "maya@example.com", "I want a refund for damaged order #1003.")

    assert response["approval_request_id"] is None
    assert response["status"] == "escalated"
    assert "shipping investigation" in response["message"].lower()
    assert demo_store.approvals == {}
