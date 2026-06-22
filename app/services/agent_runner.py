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
from app.schemas.agent_outputs import ChatResponse, InputGuardrailResult, TriageResult
from app.schemas.conversation import ConversationState
from app.services.audit_service import log_agent_event
from app.services.conversation_state import (
    add_customer_turn,
    conversation_prompt,
    enrich_triage_with_context,
    load_conversation_state,
    refund_reason_is_missing,
    remember_pending_refund_reason,
    update_state_after_response,
)


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

    conversation = load_conversation_state(session_id, customer_email)
    add_customer_turn(conversation, message)
    triage = enrich_triage_with_context(classify_message(message), conversation)

    if _refund_reason_needed(message, triage):
        return _request_refund_reason(session_id, conversation, triage)

    settings = get_settings()
    runtime = runtime_override or settings.agent_runtime

    if runtime == "local":
        response = _run_local_support_turn(
            session_id=session_id,
            customer_email=customer_email,
            message=message,
            input_review=input_review,
            conversation=conversation,
            triage=triage,
        )
        return response

    if runtime == "openai":
        runtime_settings = settings.model_copy(update={"agent_runtime": "openai"})
        try:
            validate_runtime_settings(runtime_settings)
        except RuntimeConfigError as exc:
            return _runtime_configuration_error(session_id, str(exc))

        from app.services.openai_agent_adapter import run_openai_support_turn

        response = await run_openai_support_turn(
            session_id=session_id,
            customer_email=customer_email,
            message=conversation_prompt(message, conversation),
            settings=runtime_settings,
        )
        if response.status == "needs_info" and response.intent == "refund_request" and triage.order_id is not None:
            remember_pending_refund_reason(conversation, triage.order_id)
        update_state_after_response(conversation, triage, response)
        return response

    return _runtime_configuration_error(session_id, f"Unsupported agent runtime: {runtime}")


def _run_local_support_turn(
    session_id: str,
    customer_email: str | None,
    message: str,
    input_review: InputGuardrailResult | None = None,
    conversation: ConversationState | None = None,
    triage: TriageResult | None = None,
) -> ChatResponse:
    input_review = input_review or evaluate_input(message)
    if not input_review.allowed:
        return _blocked_input_response(session_id, message, input_review)

    conversation = conversation or load_conversation_state(session_id, customer_email)
    triage = triage or enrich_triage_with_context(classify_message(message), conversation)
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
    update_state_after_response(conversation, triage, reviewed)
    return reviewed


def _refund_reason_needed(message: str, triage: TriageResult) -> bool:
    return (
        triage.intent == "refund_request"
        and triage.order_id is not None
        and refund_reason_is_missing(message)
    )


def _request_refund_reason(
    session_id: str,
    conversation: ConversationState,
    triage: TriageResult,
) -> ChatResponse:
    assert triage.order_id is not None
    remember_pending_refund_reason(conversation, triage.order_id)
    log_agent_event(
        session_id=session_id,
        agent_name="Triage Agent",
        event_type="handoff",
        payload=triage.model_dump(),
    )
    response = ChatResponse(
        ticket_id=None,
        agent="Refund Agent",
        intent=triage.intent,
        status="needs_info",
        message=(
            f"I found order #{triage.order_id}. Please share the reason for "
            "the refund request so I can check eligibility and submit it for review."
        ),
        tool_calls=[],
    )
    log_agent_event(
        session_id=session_id,
        agent_name=response.agent,
        event_type="response",
        payload=response.model_dump(),
    )
    update_state_after_response(conversation, triage, response)
    return response


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
