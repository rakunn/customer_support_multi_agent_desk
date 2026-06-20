from fastapi import APIRouter, HTTPException

from app.db.seed import demo_store
from app.schemas.ticket import Ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=list[Ticket])
async def tickets() -> list[Ticket]:
    return sorted(demo_store.tickets.values(), key=lambda ticket: ticket.updated_at, reverse=True)


@router.get("/{ticket_id}", response_model=Ticket)
async def ticket_detail(ticket_id: str) -> Ticket:
    ticket = demo_store.tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

