from fastapi.testclient import TestClient

from app.db.seed import demo_store
from app.main import app


def setup_function() -> None:
    demo_store.reset()


def test_create_order_is_available_to_order_agent() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/orders",
        json={
            "id": "1234",
            "customer_email": "maya@example.com",
            "status": "shipped",
            "amount": 64.5,
            "item_name": "Test Travel Dock",
            "shipping_status": "Label created for QA shipment",
            "delivered_at": None,
            "is_final_sale": False,
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["id"] == "1234"

    chat_response = client.post(
        "/api/chat",
        json={
            "session_id": "session_custom_order",
            "customer_email": "maya@example.com",
            "message": "Where is order #1234?",
        },
    )

    assert chat_response.status_code == 200
    payload = chat_response.json()
    assert payload["agent"] == "Order Status Agent"
    assert "Label created for QA shipment" in payload["message"]


def test_admin_reset_restores_exact_seed_orders_and_clears_workflow() -> None:
    client = TestClient(app)
    client.post(
        "/api/orders",
        json={
            "id": "1234",
            "customer_email": "maya@example.com",
            "status": "delivered",
            "amount": 24.0,
            "item_name": "Temporary QA Cable",
            "shipping_status": "Delivered for QA",
            "delivered_at": "2026-06-18T12:30:00Z",
            "is_final_sale": False,
        },
    )
    client.post(
        "/api/chat",
        json={
            "session_id": "session_reset",
            "customer_email": "maya@example.com",
            "message": "I want a refund for order #1005. It arrived damaged.",
        },
    )

    reset_response = client.post("/api/admin/reset")

    assert reset_response.status_code == 200
    assert "1234" not in demo_store.orders
    assert set(demo_store.orders) == {"1003", "1005", "1007", "1008", "1010", "2001"}
    assert demo_store.tickets == {}
    assert demo_store.approvals == {}


def test_admin_purge_workflow_keeps_orders() -> None:
    client = TestClient(app)
    client.post(
        "/api/orders",
        json={
            "id": "1234",
            "customer_email": "maya@example.com",
            "status": "processing",
            "amount": 12.0,
            "item_name": "Temporary QA Stand",
            "shipping_status": "Preparing for shipment",
            "delivered_at": None,
            "is_final_sale": False,
        },
    )
    client.post(
        "/api/chat",
        json={
            "session_id": "session_purge",
            "customer_email": "maya@example.com",
            "message": "Where is order #1234?",
        },
    )

    purge_response = client.post("/api/admin/purge-workflow")

    assert purge_response.status_code == 200
    assert "1234" in demo_store.orders
    assert demo_store.tickets == {}
    assert demo_store.agent_events == []


def test_custom_order_can_be_deleted_but_seed_order_cannot() -> None:
    client = TestClient(app)
    client.post(
        "/api/orders",
        json={
            "id": "1234",
            "customer_email": "maya@example.com",
            "status": "processing",
            "amount": 12.0,
            "item_name": "Temporary QA Stand",
            "shipping_status": "Preparing for shipment",
            "delivered_at": None,
            "is_final_sale": False,
        },
    )

    custom_delete = client.delete("/api/orders/1234")
    seed_delete = client.delete("/api/orders/1003")

    assert custom_delete.status_code == 200
    assert seed_delete.status_code == 400
    assert "1234" not in demo_store.orders
    assert "1003" in demo_store.orders
