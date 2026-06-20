from pydantic import BaseModel


class AdminStats(BaseModel):
    customers: int
    orders: int
    custom_orders: int
    tickets: int
    approvals: int
    traces: int


class AdminActionResult(BaseModel):
    status: str
    stats: AdminStats
