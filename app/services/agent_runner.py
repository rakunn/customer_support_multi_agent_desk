import asyncio

from app.agents.escalation_agent import handle_escalation
from app.agents.faq_agent import handle_faq_question
from app.agents.order_agent import handle_order_status
from app.agents.quality_review_agent import review_agent_response
from app.agents.refund_agent import handle_refund_request
from app.agents.technical_agent import handle_technical_issue
from app.agents.triage_agent import classify_message
from app.config import RuntimeConfigError, get_settings, validate_runtime_settings
from app.guardrails.input_guardrails import evaluate_input
from app.schemas.agent_outputs import ChatResponse, InputGuardrailResult
from app.services.audit_service import log_agent_event


def run_support_turn(
    session_id: str,
    customer_email: str | None,
    message: str,
    runtime_override: str | None = None,
) -> ChatResponse:
    return asyncio.run(
        run_support_turn_async(
            session_id=session_id,
            customer_email=customer_email,
            message=message,
            runtime_override=runtime_override,
        )
    )


async def run_support_turn_async(
    session_id: str,
    customer_email: str | None,
    message: str,
    runtime_override: str | None = None,
) -> ChatResponse:
    input_review = evaluate_input(message)
    if not input_review.allowed:
        return _blocked_input_response(session_id, message, input_review)

    settings = get_settings()
    runtime = runtime_override or settings.agent_runtime

    if runtime == "local":
        return _run_local_support_turn(
            session_id=session_id,
            customer_email=customer_email,
            message=message,
            input_review=input_review,
        )

    if runtime == "openai":
        runtime_settings = settings.model_copy(update={"agent_runtime": "openai"})
        try:
            validate_runtime_settings(runtime_settings)
        except RuntimeConfigError as exc:
            return _runtime_configuration_error(session_id, str(exc))

        from app.services.openai_agent_adapter import run_openai_support_turn

        return await run_openai_support_turn(
            session_id=session_id,
            customer_email=customer_email,
            message=message,
            settings=runtime_settings,
        )

    return _runtime_configuration_error(session_id, f"Unsupported agent runtime: {runtime}")


def _run_local_support_turn(
    session_id: str,
    customer_email: str | None,
    message: str,
    input_review: InputGuardrailResult | None = None,
) -> ChatResponse:
    input_review = input_review or evaluate_input(message)
    if not input_review.allowed:
        return _blocked_input_response(session_id, message, input_review)

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


def _blocked_input_response(
    session_id: str,
    message: str,
    input_review: InputGuardrailResult,
) -> ChatResponse:
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


def _runtime_configuration_error(session_id: str, error: str) -> ChatResponse:
    response = ChatResponse(
        ticket_id=None,
        agent="OpenAI Runtime",
        intent="runtime_error",
        status="configuration_error",
        message=error,
        tool_calls=[],
    )
    log_agent_event(
        session_id=session_id,
        agent_name="OpenAI Runtime",
        event_type="configuration_error",
        payload={"error": error},
    )
    return response
