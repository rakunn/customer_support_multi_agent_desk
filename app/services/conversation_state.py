import re

from app.db.seed import demo_store
from app.schemas.agent_outputs import ChatResponse, TriageResult
from app.schemas.conversation import ConversationState, ConversationTurn

REFUND_REASON_FIELD = "refund_reason"
ORDER_ID_FIELD = "order_id"
_ORDER_ID_PATTERN = re.compile(r"#?(\d{4,})")
_REFUND_REASON_TERMS = (
    "arrived",
    "damaged",
    "defective",
    "broken",
    "wrong",
    "changed my mind",
    "chargeback",
    "lawsuit",
    "scam",
    "fraud",
    "not as described",
    "missing",
    "late",
    "final sale",
    "opened",
    "does not work",
    "doesn't work",
)


def load_conversation_state(session_id: str, customer_email: str | None) -> ConversationState:
    existing = demo_store.get_conversation_state(session_id)
    if existing is None or existing.customer_email != customer_email:
        return ConversationState(session_id=session_id, customer_email=customer_email)
    return existing


def save_conversation_state(state: ConversationState) -> ConversationState:
    state.turns = state.turns[-12:]
    return demo_store.save_conversation_state(state)


def add_customer_turn(state: ConversationState, message: str) -> None:
    state.turns.append(ConversationTurn(role="customer", message=message))


def add_agent_turn(state: ConversationState, response: ChatResponse) -> None:
    state.turns.append(
        ConversationTurn(
            role="agent",
            message=response.message,
            agent=response.agent,
        )
    )


def enrich_triage_with_context(
    triage: TriageResult,
    state: ConversationState,
) -> TriageResult:
    intent = triage.intent
    agent = triage.agent
    order_id = triage.order_id

    should_use_pending_refund = (
        REFUND_REASON_FIELD in state.pending_fields
        and state.active_intent == "refund_request"
        and triage.intent in {"refund_request", "faq_policy_question"}
    )
    if should_use_pending_refund:
        intent = "refund_request"
        agent = "Refund Agent"

    if order_id is None and intent in {"refund_request", "order_status"}:
        order_id = state.active_order_id

    missing_information = [
        field
        for field in triage.missing_information
        if field != ORDER_ID_FIELD or order_id is None
    ]

    return triage.model_copy(
        update={
            "intent": intent,
            "agent": agent,
            "order_id": order_id,
            "missing_information": missing_information,
        }
    )


def refund_reason_is_missing(message: str) -> bool:
    normalized = message.lower()
    if any(term in normalized for term in _REFUND_REASON_TERMS):
        return False
    if "money back" in normalized:
        return False

    stripped = _ORDER_ID_PATTERN.sub("", normalized)
    filler_words = {
        "a",
        "an",
        "can",
        "for",
        "help",
        "i",
        "me",
        "my",
        "need",
        "of",
        "please",
        "refund",
        "return",
        "that",
        "the",
        "this",
        "want",
        "with",
        "you",
    }
    meaningful_words = [
        word
        for word in re.findall(r"[a-z']+", stripped)
        if word not in filler_words
    ]
    return len(meaningful_words) <= 2


def remember_pending_refund_reason(
    state: ConversationState,
    order_id: str,
) -> None:
    state.active_order_id = order_id
    state.active_intent = "refund_request"
    if REFUND_REASON_FIELD not in state.pending_fields:
        state.pending_fields.append(REFUND_REASON_FIELD)


def update_state_after_response(
    state: ConversationState,
    triage: TriageResult,
    response: ChatResponse,
) -> None:
    if response.status != "blocked" and triage.order_id is not None:
        state.active_order_id = triage.order_id
    if response.status != "blocked":
        state.active_intent = triage.intent
    if response.status != "needs_info":
        state.pending_fields = []
    add_agent_turn(state, response)
    save_conversation_state(state)


def conversation_prompt(message: str, state: ConversationState) -> str:
    context_lines: list[str] = []
    if state.active_order_id:
        context_lines.append(f"active_order_id: {state.active_order_id}")
    if state.active_intent:
        context_lines.append(f"active_intent: {state.active_intent}")
    if state.pending_fields:
        context_lines.append(f"pending_fields: {', '.join(state.pending_fields)}")

    if not context_lines:
        return message

    context = "\n".join(context_lines)
    if REFUND_REASON_FIELD in state.pending_fields and state.active_order_id:
        return (
            "Continue the pending refund workflow using the verified app conversation context. "
            "Do not ask again for the order ID.\n"
            f"{context}\n"
            "Treat the customer message as refund_reason.\n\n"
            f"Customer message: {message}"
        )

    return (
        "Use this verified app conversation context when it is relevant. "
        "Do not ask again for a known active_order_id unless the customer changes it.\n"
        f"{context}\n\nCustomer message: {message}"
    )
