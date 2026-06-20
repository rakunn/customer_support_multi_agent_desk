from app.db.seed import demo_store
from app.schemas.agent_outputs import ToolError
from app.schemas.customer import Customer
from app.schemas.order import Order


def lookup_customer(customer_email: str) -> Customer | ToolError:
    normalized_email = customer_email.strip().lower()
    for customer in demo_store.customers.values():
        if customer.email.lower() == normalized_email:
            return customer
    return ToolError(
        code="customer_not_found",
        message="No customer record was found for that email address.",
    )


def get_customer(customer_id: str) -> Customer | ToolError:
    customer = demo_store.customers.get(customer_id)
    if customer is None:
        return ToolError(
            code="customer_not_found",
            message="No customer record was found for that customer ID.",
        )
    return customer


def list_customer_orders(customer_id: str) -> list[Order] | ToolError:
    if customer_id not in demo_store.customers:
        return ToolError(
            code="customer_not_found",
            message="No customer record was found for that customer ID.",
        )
    return [order for order in demo_store.orders.values() if order.customer_id == customer_id]

