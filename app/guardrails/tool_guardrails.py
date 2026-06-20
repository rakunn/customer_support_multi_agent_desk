from app.schemas.refund import RefundEligibilityResult


def refund_requires_approval(eligibility: RefundEligibilityResult) -> bool:
    return eligibility.approval_required or not eligibility.eligible
