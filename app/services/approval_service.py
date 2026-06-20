from app.db.seed import demo_store, utc_now
from app.schemas.agent_outputs import ToolError
from app.schemas.refund import ApprovalDecisionResponse, ApprovalRequest, RefundResult
from app.tools.refund_tools import issue_mock_refund
from app.tools.ticket_tools import update_ticket


def list_approval_requests(status: str | None = None) -> list[ApprovalRequest]:
    approvals = list(demo_store.approvals.values())
    if status is not None:
        approvals = [approval for approval in approvals if approval.status == status]
    return sorted(approvals, key=lambda approval: approval.created_at)


def approve_refund_request(approval_id: str) -> ApprovalDecisionResponse | ToolError:
    approval = demo_store.approvals.get(approval_id)
    if approval is None:
        return ToolError(
            code="approval_not_found",
            message="No approval request was found for that ID.",
        )

    if demo_store.is_order_refunded(approval.order_id):
        return ToolError(
            code="refund_already_processed",
            message="A refund has already been processed for that order.",
        )

    approved = approval.model_copy(update={"status": "approved", "updated_at": utc_now()})
    demo_store.save_approval(approved)
    refund_result = issue_mock_refund(approval_id)
    if isinstance(refund_result, ToolError):
        return refund_result

    if approved.ticket_id:
        update_ticket(approved.ticket_id, "resolved", f"Approved refund {approved.id} was processed.")

    return ApprovalDecisionResponse(approval=approved, refund_result=refund_result)


def reject_refund_request(approval_id: str) -> ApprovalDecisionResponse | ToolError:
    approval = demo_store.approvals.get(approval_id)
    if approval is None:
        return ToolError(
            code="approval_not_found",
            message="No approval request was found for that ID.",
        )

    rejected = approval.model_copy(update={"status": "rejected", "updated_at": utc_now()})
    demo_store.save_approval(rejected)
    if rejected.ticket_id:
        update_ticket(rejected.ticket_id, "escalated", f"Rejected refund {rejected.id}; human follow-up required.")

    return ApprovalDecisionResponse(approval=rejected, refund_result=None)
