from app.schemas.agent_outputs import OutputGuardrailResult

UNSUPPORTED_REFUND_PROMISES = (
    "refund has been issued",
    "refund has been processed",
    "refund is issued",
    "refund is processed",
)


def review_output(
    message: str,
    tool_calls: list[str],
    approval_request_id: str | None = None,
) -> OutputGuardrailResult:
    normalized = message.lower()
    refund_was_processed = "issue_mock_refund" in tool_calls
    promised_refund = any(pattern in normalized for pattern in UNSUPPORTED_REFUND_PROMISES)

    if promised_refund and not refund_was_processed:
        if approval_request_id:
            safe_message = (
                "I prepared the refund request, and it is pending human approval "
                "before any refund action can happen."
            )
        else:
            safe_message = (
                "I can review the refund request against policy, but I cannot promise "
                "a refund before the required checks are complete."
            )
        return OutputGuardrailResult(
            allowed=False,
            reason="unsupported_refund_promise",
            safe_message=safe_message,
        )

    return OutputGuardrailResult(allowed=True, safe_message=message)

