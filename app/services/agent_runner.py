from app.agents.escalation_agent import handle_escalation
from app.agents.faq_agent import handle_faq_question
from app.agents.order_agent import handle_order_status
from app.agents.quality_review_agent import review_agent_response
from app.agents.refund_agent import handle_refund_request
from app.agents.technical_agent import handle_technical_issue
from app.agents.triage_agent import classify_message
from app.guardrails.input_guardrails import evaluate_input
from app.schemas.agent_outputs import ChatResponse
from app.services.audit_service import log_agent_event


def run_support_turn(
    session_id: str,
    customer_email: str | None,
    message: str,
) -> ChatResponse:
    input_review = evaluate_input(message)
    if not input_review.allowed:
        response = ChatResponse(
            ticket_id=None,
            agent="Triage Agent",
            intent=input_review.intent,
            status="blocked",
            message=input_review.safe_message,
            tool_calls=[],
        )
        log_agent_event(
            session_id=session_id,
            agent_name="Triage Agent",
            event_type=input_review.reason or "input_guardrail",
            payload={"message": message, "intent": input_review.intent},
        )
        return response

    triage = classify_message(message)
    log_agent_event(
        session_id=session_id,
        agent_name="Triage Agent",
        event_type="handoff",
        payload=triage.model_dump(),
    )

    if triage.intent == "refund_request":
        response = handle_refund_request(session_id, customer_email, message, triage)
    elif triage.intent == "order_status":
        response = handle_order_status(session_id, customer_email, message, triage)
    elif triage.intent == "technical_issue":
        response = handle_technical_issue(session_id, customer_email, message, triage)
    elif triage.intent == "human_escalation":
        response = handle_escalation(session_id, customer_email, message, triage)
    else:
        response = handle_faq_question(session_id, customer_email, message, triage)

    reviewed = review_agent_response(response)
    log_agent_event(
        session_id=session_id,
        agent_name=reviewed.agent,
        event_type="response",
        payload=reviewed.model_dump(),
    )
    return reviewed

