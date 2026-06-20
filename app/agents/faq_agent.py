from app.schemas.agent_outputs import ChatResponse, ToolError, TriageResult
from app.tools.customer_tools import lookup_customer
from app.tools.kb_tools import search_knowledge_base
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
        if not isinstance(customer, ToolError):
            customer_id = customer.id

    tool_calls.append("search_knowledge_base")
    kb_results = search_knowledge_base(message, top_k=3)
    ticket = create_ticket(customer_id, triage.intent, triage.summary, triage.priority)
    tool_calls.append("create_ticket")

    if not kb_results:
        return ChatResponse(
            ticket_id=ticket.id,
            agent="FAQ Agent",
            intent=triage.intent,
            status=ticket.status,
            message=(
                "I cannot confirm that from the current support policy documents. "
                "I can escalate this to a human support representative for review."
            ),
            tool_calls=tool_calls,
        )

    top_result = kb_results[0]
    return ChatResponse(
        ticket_id=ticket.id,
        agent="FAQ Agent",
        intent=triage.intent,
        status=ticket.status,
        message=(
            f"According to {top_result.policy_id}, {top_result.content} "
            "I can escalate this if your case does not match that policy."
        ),
        tool_calls=tool_calls,
    )
