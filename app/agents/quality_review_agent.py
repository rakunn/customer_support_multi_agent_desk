from app.guardrails.output_guardrails import review_output
from app.schemas.agent_outputs import ChatResponse


def review_agent_response(response: ChatResponse) -> ChatResponse:
    review = review_output(
        message=response.message,
        tool_calls=response.tool_calls,
        approval_request_id=response.approval_request_id,
    )
    if review.allowed:
        return response
    return response.model_copy(update={"message": review.safe_message})
