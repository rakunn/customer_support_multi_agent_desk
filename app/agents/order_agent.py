from app.schemas.agent_outputs import ChatResponse, ToolError, TriageResult
from app.tools.customer_tools import lookup_customer
from app.tools.order_tools import lookup_order
from app.tools.ticket_tools import create_ticket


def handle_order_status(
    session_id: str,
    customer_email: str | None,
    message: str,
    triage: TriageResult,
) -> ChatResponse:
    tool_calls: list[str] = []

    customer_id = None
    if customer_email:
        tool_calls.append("lookup_customer")
        customer = lookup_customer(customer_email)
        if not isinstance(customer, ToolError):
            customer_id = customer.id

    if triage.order_id is None:
        ticket = create_ticket(customer_id, triage.intent, "Missing order ID for order-status request.", triage.priority)
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Order Status Agent",
            intent=triage.intent,
            status=ticket.status,
            message="Please share the order number so I can look up the shipment status.",
            tool_calls=tool_calls,
        )

    tool_calls.append("lookup_order")
    order = lookup_order(triage.order_id)
    if isinstance(order, ToolError):
        ticket = create_ticket(customer_id, triage.intent, "Order status request for unknown order.", "medium")
        tool_calls.append("create_ticket")
        return ChatResponse(
            ticket_id=ticket.id,
            agent="Order Status Agent",
            intent=triage.intent,
            status=ticket.status,
            message="I could not find that order. Please verify the order number or contact details.",
            tool_calls=tool_calls,
        )

    ticket = create_ticket(customer_id or order.customer_id, triage.intent, f"Order status lookup for #{order.id}.", triage.priority)
    tool_calls.append("create_ticket")
    return ChatResponse(
        ticket_id=ticket.id,
        agent="Order Status Agent",
        intent=triage.intent,
        status=ticket.status,
        message=(
            f"Order #{order.id} is currently {order.status}. "
            f"Carrier status: {order.shipping_status}."
        ),
        tool_calls=tool_calls,
    )

