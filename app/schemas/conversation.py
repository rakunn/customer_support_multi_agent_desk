from typing import Literal

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: Literal["customer", "agent"]
    message: str
    agent: str | None = None


class ConversationState(BaseModel):
    session_id: str
    customer_email: str | None = None
    active_order_id: str | None = None
    active_intent: str | None = None
    pending_fields: list[str] = Field(default_factory=list)
    turns: list[ConversationTurn] = Field(default_factory=list)
