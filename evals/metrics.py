from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    message: str
    customer_email: str = "maya@example.com"
    expected_intent: str
    expected_agent: str
    expected_tools: list[str] = Field(default_factory=list)
    expected_guardrail: str | None = None
    expected_approval_required: bool | None = None


class EvalReport(BaseModel):
    total_cases: int
    routing_accuracy: float
    specialist_accuracy: float
    required_tool_accuracy: float
    refund_decision_accuracy: float
    guardrail_pass_rate: float
    unsupported_refund_promise_rate: float
