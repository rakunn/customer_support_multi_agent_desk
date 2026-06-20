from fastapi import APIRouter, HTTPException

from app.schemas.agent_outputs import ToolError
from app.schemas.refund import ApprovalDecisionResponse, ApprovalRequest
from app.services.approval_service import (
    approve_refund_request,
    list_approval_requests,
    reject_refund_request,
)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRequest])
async def approvals(status: str | None = None) -> list[ApprovalRequest]:
    return list_approval_requests(status=status)


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve(approval_id: str) -> ApprovalDecisionResponse:
    result = approve_refund_request(approval_id)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=404, detail=result.model_dump())
    return result


@router.post("/{approval_id}/reject", response_model=ApprovalDecisionResponse)
async def reject(approval_id: str) -> ApprovalDecisionResponse:
    result = reject_refund_request(approval_id)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=404, detail=result.model_dump())
    return result

