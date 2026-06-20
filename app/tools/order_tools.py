from app.db.seed import demo_store
from app.schemas.agent_outputs import ToolError
from app.schemas.order import Order


def lookup_order(order_id: str) -> Order | ToolError:
    normalized_order_id = order_id.strip().removeprefix("#")
    order = demo_store.orders.get(normalized_order_id)
    if order is None:
        return ToolError(
            code="order_not_found",
            message="No order was found for that order ID.",
        )
    return order

