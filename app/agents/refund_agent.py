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

    ticket = create_ticket(
        customer_id or order.customer_id,
        triage.intent,
        f"Refund request for order #{order.id}.",
        triage.priority,
    )
    tool_calls.append("create_ticket")

    if refund_requires_approval(eligibility):
        approval = create_refund_approval_request(order.id, message, eligibility.amount, ticket.id)
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

