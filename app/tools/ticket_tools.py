from app.db.seed import demo_store, utc_now
from app.schemas.agent_outputs import ToolError
from app.schemas.ticket import Priority, Ticket, TicketStatus

DEFAULT_TEAM_BY_INTENT = {
    "faq_policy_question": "support",
    "order_status": "shipping",
    "refund_request": "refunds",
    "technical_issue": "technical_support",
    "billing_issue": "billing",
    "human_escalation": "support",
}


def create_ticket(customer_id: str | None, issue_type: str, summary: str, priority: Priority) -> Ticket:
    now = utc_now()
    ticket = Ticket(
        id=demo_store.next_ticket_id(),
        customer_id=customer_id,
        intent=issue_type,
        priority=priority,
        status="open",
        summary=summary,
        assigned_team=DEFAULT_TEAM_BY_INTENT.get(issue_type, "support"),
        notes=[],
        created_at=now,
        updated_at=now,
    )
    return demo_store.save_ticket(ticket)


def update_ticket(ticket_id: str, status: TicketStatus, note: str) -> Ticket | ToolError:
    ticket = demo_store.tickets.get(ticket_id)
    if ticket is None:
        return ToolError(
            code="ticket_not_found",
            message="No ticket was found for that ticket ID.",
        )
    updated = ticket.model_copy(update={
        "status": status,
        "notes": [*ticket.notes, note],
        "updated_at": utc_now(),
    })
    return demo_store.save_ticket(updated)


def assign_ticket(ticket_id: str, team: str) -> Ticket | ToolError:
    ticket = demo_store.tickets.get(ticket_id)
    if ticket is None:
        return ToolError(
            code="ticket_not_found",
            message="No ticket was found for that ticket ID.",
        )
    updated = ticket.model_copy(update={"assigned_team": team, "updated_at": utc_now()})
    return demo_store.save_ticket(updated)
