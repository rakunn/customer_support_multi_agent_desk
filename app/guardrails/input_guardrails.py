from app.schemas.agent_outputs import InputGuardrailResult

PROMPT_INJECTION_PATTERNS = (
    "ignore your instructions",
    "ignore all rules",
    "ignore previous",
    "bypass policy",
    "bypass approval",
    "system prompt",
    "refund every",
    "refund all",
)

OFF_TOPIC_PATTERNS = (
    "homework",
    "essay",
    "write my paper",
    "dating advice",
    "stock tip",
    "weather forecast",
)


def evaluate_input(message: str) -> InputGuardrailResult:
    normalized = message.strip().lower()

    if any(pattern in normalized for pattern in PROMPT_INJECTION_PATTERNS):
        return InputGuardrailResult(
            allowed=False,
            intent="unsafe_or_prompt_injection",
            reason="prompt_injection_guardrail",
            safe_message=(
                "I can help with support requests, but I cannot bypass refund policy "
                "or approval requirements."
            ),
        )

    if any(pattern in normalized for pattern in OFF_TOPIC_PATTERNS):
        return InputGuardrailResult(
            allowed=False,
            intent="off_topic",
            reason="support_scope_guardrail",
            safe_message="I can help with orders, refunds, policies, billing, or technical support.",
        )

    return InputGuardrailResult(
        allowed=True,
        intent="support_request",
        safe_message=message,
    )

