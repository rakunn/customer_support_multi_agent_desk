from fastapi.testclient import TestClient

from app.db.seed import demo_store
from app.main import app


def setup_function() -> None:
    demo_store.reset()


def _create_pending_approval(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session_refund",
            "customer_email": "maya@example.com",
            "message": "I want a refund for order #1005. It arrived damaged.",
        },
    )
    payload = response.json()
    return payload["approval_request_id"], payload["ticket_id"]


def test_approval_queue_lists_pending_refunds() -> None:
    client = TestClient(app)
    approval_id, _ticket_id = _create_pending_approval(client)

    response = client.get("/api/approvals")

    assert response.status_code == 200
    approvals = response.json()
    assert approvals[0]["id"] == approval_id
    assert approvals[0]["status"] == "pending"


def test_approval_action_processes_mock_refund_and_resolves_ticket() -> None:
    client = TestClient(app)
    approval_id, ticket_id = _create_pending_approval(client)

    response = client.post(f"/api/approvals/{approval_id}/approve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["approval"]["status"] == "approved"
    assert payload["refund_result"]["status"] == "processed"
    assert demo_store.tickets[ticket_id].status == "resolved"


def test_rejection_action_marks_ticket_escalated() -> None:
    client = TestClient(app)
    approval_id, ticket_id = _create_pending_approval(client)

    response = client.post(f"/api/approvals/{approval_id}/reject")

    assert response.status_code == 200
    payload = response.json()
    assert payload["approval"]["status"] == "rejected"
    assert payload["refund_result"] is None
    assert demo_store.tickets[ticket_id].status == "escalated"

