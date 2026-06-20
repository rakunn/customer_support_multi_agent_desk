import re

from app.schemas.agent_outputs import TriageResult

ORDER_ID_PATTERN = re.compile(r"#?(\d{4,})")


def _extract_order_id(message: str) -> str | None:
    match = ORDER_ID_PATTERN.search(message)
    if match is None:
        return None
    return match.group(1)


def _priority_for(message: str, intent: str) -> str:
    normalized = message.lower()
    if any(word in normalized for word in ("urgent", "lawsuit", "chargeback", "angry")):
        return "urgent"
    if intent in {"refund_request", "technical_issue"}:
        return "high"
    if intent == "order_status":
        return "medium"
    return "low"


def classify_message(message: str) -> TriageResult:
    normalized = message.lower()
    order_id = _extract_order_id(message)

    if any(term in normalized for term in ("policy", "shipping", "ship internationally", "warranty", "opened items")):
        intent = "faq_policy_question"
        agent = "FAQ Agent"
    elif any(term in normalized for term in ("refund", "return", "money back", "damaged")):
        intent = "refund_request"
        agent = "Refund Agent"
    elif any(term in normalized for term in ("where is order", "track", "tracking", "package", "delivery")):
        intent = "order_status"
        agent = "Order Status Agent"
    elif any(term in normalized for term in ("crash", "upload", "sync", "password", "integration", "bug")):
        intent = "technical_issue"
        agent = "Technical Support Agent"
    elif any(term in normalized for term in ("human", "manager", "representative", "escalate")):
        intent = "human_escalation"
        agent = "Escalation Agent"
    else:
        intent = "faq_policy_question"
        agent = "FAQ Agent"

    missing_information: list[str] = []
    if intent in {"refund_request", "order_status"} and order_id is None:
        missing_information.append("order_id")

    return TriageResult(
        intent=intent,
        agent=agent,
        priority=_priority_for(message, intent),
        summary=message.strip()[:180],
        order_id=order_id,
        missing_information=missing_information,
    )
