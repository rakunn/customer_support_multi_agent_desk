from fastapi import APIRouter, HTTPException

from app.db.seed import demo_store
from app.schemas.agent_outputs import ToolError
from app.schemas.order import CreateOrderRequest, Order, OrderAdminRecord, OrderItem
from app.tools.customer_tools import lookup_customer

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[OrderAdminRecord])
async def orders() -> list[OrderAdminRecord]:
    return [
        OrderAdminRecord(order=order, is_seed=demo_store.is_seed_order(order.id))
        for order in sorted(demo_store.orders.values(), key=lambda item: item.id)
    ]


@router.post("", response_model=Order)
async def create_order(request: CreateOrderRequest) -> Order:
    customer = lookup_customer(request.customer_email)
    if isinstance(customer, ToolError):
        raise HTTPException(status_code=404, detail=customer.model_dump())

    order_id = request.id.strip().removeprefix("#")
    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID is required")

    if demo_store.is_seed_order(order_id):
        raise HTTPException(status_code=400, detail="Seed orders cannot be replaced from the admin UI")

    order = Order(
        id=order_id,
        customer_id=customer.id,
        status=request.status,
        amount=request.amount,
        items=[
            OrderItem(
                sku=f"custom-{order_id}",
                name=request.item_name,
                quantity=1,
                price=request.amount,
            )
        ],
        shipping_status=request.shipping_status,
        delivered_at=request.delivered_at,
        is_final_sale=request.is_final_sale,
    )
    return demo_store.save_order(order, is_seed=False)


@router.delete("/{order_id}")
async def delete_order(order_id: str) -> dict[str, str]:
    normalized_order_id = order_id.strip().removeprefix("#")
    if demo_store.is_seed_order(normalized_order_id):
        raise HTTPException(status_code=400, detail="Seed orders cannot be deleted")
    deleted = demo_store.delete_custom_order(normalized_order_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom order not found")
    return {"status": "deleted"}

