from app.schemas.agent_outputs import ChatResponse, TriageResult
from app.tools.customer_tools import lookup_customer
from app.tools.ticket_tools import create_ticket


def handle_faq_question(
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
    return ChatResponse(
        ticket_id=ticket.id,
        agent="FAQ Agent",
        intent=triage.intent,
        status=ticket.status,
        message=(
            "I can answer policy questions from the support knowledge base. "
            "I will check the policy documents before making a specific claim."
        ),
        tool_calls=tool_calls,
    )

