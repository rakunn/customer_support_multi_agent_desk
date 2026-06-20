from app.db.seed import demo_store
from app.guardrails.tool_guardrails import refund_requires_approval
from app.schemas.agent_outputs import ChatResponse, ToolError, TriageResult
from app.schemas.refund import RefundEligibilityResult
from app.tools.customer_tools import lookup_customer
from app.tools.order_tools import lookup_order
from app.tools.refund_tools import check_refund_eligibility, create_refund_approval_request
from app.tools.ticket_tools import create_ticket, update_ticket


def handle_refund_request(
    session_id: str,
    customer_email: str | None,
    message: str,
    triage: TriageResult,
) -> ChatResponse:
    tool_calls: list[str] = []
    customer_id = None

    if customer_email:
        tool_calls.append("lookup_customer")
        customer = lookup_customer(customer_email)
        if not isinstance(customer, ToolError):
            customer_id = customer.id

    if customer_id is None:
        ticket = create_ticket(None, triage.intent, "Refund request without verified customer.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status="blocked",
            message="Please verify the customer email before I can review a refund for an order.",
            tool_calls=tool_calls,
        )

    if triage.order_id is None:
        ticket = create_ticket(customer_id, triage.intent, "Refund request missing order ID.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status=ticket.status,
            message="Please share the order number so I can check the refund policy.",
            tool_calls=tool_calls,
        )

    tool_calls.append("lookup_order")
    order = lookup_order(triage.order_id)
    if isinstance(order, ToolError):
        ticket = create_ticket(customer_id, triage.intent, "Refund request for unknown order.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status=ticket.status,
            message="I could not find that order. Please verify the order number before I review a refund.",
            tool_calls=tool_calls,
        )

    if order.customer_id != customer_id:
        ticket = create_ticket(customer_id, triage.intent, "Refund request for order outside customer account.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status="blocked",
            message=(
                "I can only review refunds for orders on the current customer account. "
                "Please verify the customer email or order number."
            ),
            tool_calls=tool_calls,
        )

    existing_refund_response = _existing_pending_refund_response(order.id, triage.intent, tool_calls)
    if existing_refund_response is not None:
        return existing_refund_response

    if demo_store.is_order_refunded(order.id):
        return ChatResponse(
            ticket_id=None,
            agent="Refund Agent",
            intent=triage.intent,
            status="resolved",
            message="A refund has already been processed for that order, so I cannot create another refund request.",
            tool_calls=tool_calls,
        )

    tool_calls.append("check_refund_eligibility")
    eligibility = check_refund_eligibility(order.id, message)
    if not isinstance(eligibility, RefundEligibilityResult):
        ticket = create_ticket(customer_id or order.customer_id, triage.intent, "Refund eligibility lookup failed.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status=ticket.status,
            message="I could not verify the refund policy for that order yet. I can escalate this for review.",
            tool_calls=tool_calls,
        )

    if "not_delivered" in eligibility.risk_flags:
        ticket = create_ticket(
            customer_id,
            "order_status",
            f"Damage claim before delivery for order #{order.id}.",
            triage.priority,
        )
        tool_calls.append("create_ticket")
        updated_ticket = update_ticket(ticket.id, "escalated", "Order is not delivered; shipping investigation required.")
        tool_calls.append("update_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status=updated_ticket.status if not isinstance(updated_ticket, ToolError) else "escalated",
            message=(
                "That order has not been delivered yet, so I cannot start a refund. "
                "I escalated it as a shipping investigation."
            ),
            tool_calls=tool_calls,
        )

    ticket = create_ticket(
        customer_id or order.customer_id,
        triage.intent,
        f"Refund request for order #{order.id}.",
        triage.priority,
    )
    tool_calls.append("create_ticket")

    if refund_requires_approval(eligibility):
        approval = create_refund_approval_request(
            order_id=order.id,
            customer_id=customer_id,
            reason=message,
            amount=eligibility.amount,
            ticket_id=ticket.id,
        )
        tool_calls.append("create_refund_approval_request")
        if isinstance(approval, ToolError):
            return ChatResponse(
                ticket_id=ticket.id,
                agent="Refund Agent",
                intent=triage.intent,
                status=ticket.status,
                message="I could not create the approval request. I can escalate this to a support manager.",
                tool_calls=tool_calls,
            )
        updated_ticket = update_ticket(ticket.id, "pending_approval", f"Approval {approval.id} requested.")
        tool_calls.append("update_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Refund Agent",
            intent=triage.intent,
            status=updated_ticket.status if not isinstance(updated_ticket, ToolError) else "pending_approval",
            message=(
                "I found your order and prepared a refund request. Because this refund "
                "requires approval, I sent it to a support manager for review."
            ),
            approval_request_id=approval.id,
            tool_calls=tool_calls,
        )

    return ChatResponse(
        ticket_id=ticket.id,
        agent="Refund Agent",
        intent=triage.intent,
        status=ticket.status,
        message="Your order appears eligible under the refund policy, so I prepared it for standard processing.",
        tool_calls=tool_calls,
    )


def _existing_pending_refund_response(order_id: str, intent: str, tool_calls: list[str]) -> ChatResponse | None:
    existing_approval = demo_store.find_refund_approval(order_id, statuses={"pending"})
    if existing_approval is None:
        return None
    return ChatResponse(
        ticket_id=existing_approval.ticket_id,
        agent="Refund Agent",
        intent=intent,
        status="pending_approval",
        message=(
            "A refund request for that order is already waiting for support manager review. "
            "I will keep this with the existing approval request."
        ),
        approval_request_id=existing_approval.id,
        tool_calls=tool_calls,
    )
