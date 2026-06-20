from __future__ import annotations

from datetime import date

from app.config import get_settings
from app.db.seed import demo_store, utc_now
from app.schemas.agent_outputs import ToolError
from app.schemas.refund import ApprovalRequest, RefundEligibilityResult, RefundResult
from app.tools.customer_tools import get_customer
from app.tools.order_tools import lookup_order

DEMO_TODAY = date(2026, 6, 20)
REFUND_WINDOW_DAYS = 30


def check_refund_eligibility(order_id: str, reason: str) -> RefundEligibilityResult | ToolError:
    order = lookup_order(order_id)
    if isinstance(order, ToolError):
        return order

    customer = get_customer(order.customer_id)
    if isinstance(customer, ToolError):
        return customer

    days_since_delivery = None
    if order.delivered_at is not None:
        days_since_delivery = (DEMO_TODAY - order.delivered_at.date()).days

    risk_flags: list[str] = []
    eligible = True

    if order.is_final_sale:
        risk_flags.append("final_sale")
        eligible = False

    if days_since_delivery is None:
        risk_flags.append("not_delivered")
        eligible = False
    elif days_since_delivery > REFUND_WINDOW_DAYS:
        risk_flags.append("outside_return_window")
        eligible = False

    if order.amount > get_settings().refund_auto_approval_limit:
        risk_flags.append("amount_above_auto_limit")

    if customer.refund_count_90d >= 3:
        risk_flags.append("high_refund_frequency")

    if any(term in reason.lower() for term in ("chargeback", "lawsuit", "scam", "fraud")):
        risk_flags.append("sensitive_or_abusive_reason")

    approval_required = bool(risk_flags)
    if eligible and not approval_required:
        decision_reason = "Refund can be prepared automatically under the demo policy."
    elif eligible:
        decision_reason = "Refund appears policy-eligible but requires human approval."
    else:
        decision_reason = "Refund is not automatically eligible and requires human review."

    return RefundEligibilityResult(
        order_id=order.id,
        eligible=eligible,
        approval_required=approval_required,
        amount=order.amount,
        policy_window_days=REFUND_WINDOW_DAYS,
        days_since_delivery=days_since_delivery,
        risk_flags=risk_flags,
        decision_reason=decision_reason,
    )


def create_refund_approval_request(
    order_id: str,
    customer_id: str,
    reason: str,
    amount: float,
    ticket_id: str | None = None,
) -> ApprovalRequest | ToolError:
    order = lookup_order(order_id)
    if isinstance(order, ToolError):
        return order

    if order.customer_id != customer_id:
        return ToolError(
            code="order_customer_mismatch",
            message="That order does not belong to the verified customer.",
        )

    existing_pending = demo_store.find_refund_approval(order_id, statuses={"pending"})
    if existing_pending is not None:
        return existing_pending

    if demo_store.is_order_refunded(order_id):
        return ToolError(
            code="refund_already_processed",
            message="A refund has already been processed for that order.",
        )

    eligibility = check_refund_eligibility(order.id, reason)
    if isinstance(eligibility, ToolError):
        return eligibility

    now = utc_now()
    risk_reason = ", ".join(eligibility.risk_flags) or "manager_review"
    approval = ApprovalRequest(
        id=demo_store.next_approval_id(),
        ticket_id=ticket_id,
        order_id=eligibility.order_id,
        amount=amount,
        reason=reason,
        risk_reason=risk_reason,
        created_at=now,
        updated_at=now,
    )
    return demo_store.save_approval(approval)


def issue_mock_refund(approval_id: str) -> RefundResult | ToolError:
    approval = demo_store.approvals.get(approval_id)
    if approval is None:
        return ToolError(
            code="approval_not_found",
            message="No approval request was found for that ID.",
        )

    if approval.status != "approved":
        return ToolError(
            code="approval_not_approved",
            message="Refund cannot be issued until a human approver approves the request.",
        )

    if approval.id in demo_store.refunded_approval_ids or demo_store.is_order_refunded(approval.order_id):
        return ToolError(
            code="refund_already_processed",
            message="This approval has already been processed.",
        )

    demo_store.mark_refunded(approval.id, approval.order_id)
    return RefundResult(
        approval_id=approval.id,
        order_id=approval.order_id,
        amount=approval.amount,
        status="processed",
        message="Refund processed in the mock system.",
        processed_at=utc_now(),
    )
