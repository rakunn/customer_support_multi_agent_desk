from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ApprovalStatus = Literal["pending", "approved", "rejected", "escalated"]


class RefundEligibilityResult(BaseModel):
    order_id: str
    eligible: bool
    approval_required: bool
    amount: float = Field(ge=0)
    policy_window_days: int
    days_since_delivery: int | None
    risk_flags: list[str]
    decision_reason: str


class ApprovalRequest(BaseModel):
    id: str
    ticket_id: str | None
    order_id: str
    action_type: Literal["refund"] = "refund"
    amount: float = Field(ge=0)
    status: ApprovalStatus = "pending"
    reason: str
    risk_reason: str
    created_at: datetime
    updated_at: datetime


class RefundResult(BaseModel):
    approval_id: str
    order_id: str
    amount: float = Field(ge=0)
    status: Literal["processed"]
    message: str
    processed_at: datetime

