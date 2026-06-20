from app.schemas.agent_outputs import ChatResponse, TriageResult
from app.tools.customer_tools import lookup_customer
from app.tools.ticket_tools import create_ticket, update_ticket


def handle_escalation(
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
        if not hasattr(customer, "code"):
            customer_id = customer.id

    ticket = create_ticket(customer_id, triage.intent, triage.summary, triage.priority)
    tool_calls.append("create_ticket")
    updated = update_ticket(ticket.id, "escalated", "Customer requested human escalation.")
    tool_calls.append("update_ticket")
    return ChatResponse(
        ticket_id=ticket.id,
        agent="Escalation Agent",
        intent=triage.intent,
        status=updated.status if not hasattr(updated, "code") else "escalated",
        message="I prepared a handoff summary and escalated this to a human support representative.",
        tool_calls=tool_calls,
    )

