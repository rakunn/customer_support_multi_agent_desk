from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    ok: Literal[False] = False
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    name: str
    ok: bool
    summary: str


class InputGuardrailResult(BaseModel):
    allowed: bool
    intent: str
    reason: str | None = None
    safe_message: str


class OutputGuardrailResult(BaseModel):
    allowed: bool
    reason: str | None = None
    safe_message: str


class TriageResult(BaseModel):
    intent: str
    agent: str
    priority: Literal["low", "medium", "high", "urgent"]
    summary: str
    order_id: str | None = None
    missing_information: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    customer_email: str | None = None
    message: str


class ChatResponse(BaseModel):
    ticket_id: str | None
    agent: str
    intent: str
    status: str
    message: str
    approval_request_id: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
