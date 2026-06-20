from app.db.seed import demo_store
from app.schemas.agent_outputs import ToolError
from app.schemas.refund import RefundEligibilityResult
from app.tools.customer_tools import list_customer_orders, lookup_customer
from app.tools.order_tools import lookup_order
from app.tools.refund_tools import (
    check_refund_eligibility,
    create_refund_approval_request,
    issue_mock_refund,
)
from app.tools.ticket_tools import assign_ticket, create_ticket, update_ticket


def setup_function() -> None:
    demo_store.reset()


def test_lookup_customer_returns_typed_customer() -> None:
    customer = lookup_customer("maya@example.com")

    assert not isinstance(customer, ToolError)
    assert customer.id == "cust_001"
    assert customer.email == "maya@example.com"


def test_list_customer_orders_returns_orders_for_customer() -> None:
    orders = list_customer_orders("cust_001")

    assert not isinstance(orders, ToolError)
    assert {order.id for order in orders} == {"1003", "1005", "1010"}


def test_lookup_order_returns_safe_error_for_unknown_id() -> None:
    result = lookup_order("missing-order")

    assert isinstance(result, ToolError)
    assert result.code == "order_not_found"
    assert "missing-order" not in result.message


def test_ticket_tools_create_update_and_assign_ticket() -> None:
    created = create_ticket(
        customer_id="cust_001",
        issue_type="refund_request",
        summary="Customer reports damaged item.",
        priority="high",
    )

    assert not isinstance(created, ToolError)
    assert created.id.startswith("ticket_")
    assert created.status == "open"

    updated = update_ticket(created.id, status="pending_approval", note="Refund approval requested.")
    assigned = assign_ticket(created.id, team="refunds")

    assert not isinstance(updated, ToolError)
    assert not isinstance(assigned, ToolError)
    assert updated.status == "pending_approval"
    assert assigned.assigned_team == "refunds"


def test_high_value_refund_requires_human_approval() -> None:
    result = check_refund_eligibility("1005", "Item arrived damaged.")

    assert isinstance(result, RefundEligibilityResult)
    assert result.eligible is True
    assert result.approval_required is True
    assert result.amount == 125.0
    assert "amount_above_auto_limit" in result.risk_flags


def test_final_sale_refund_is_not_auto_eligible() -> None:
    result = check_refund_eligibility("1010", "Changed my mind.")

    assert isinstance(result, RefundEligibilityResult)
    assert result.eligible is False
    assert result.approval_required is True
    assert "final_sale" in result.risk_flags


def test_pending_approval_cannot_issue_refund() -> None:
    approval = create_refund_approval_request(
        order_id="1005",
        reason="Item arrived damaged.",
        amount=125.0,
        ticket_id="ticket_demo",
    )

    assert not isinstance(approval, ToolError)

    result = issue_mock_refund(approval.id)

    assert isinstance(result, ToolError)
    assert result.code == "approval_not_approved"
