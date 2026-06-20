from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CustomerTier = Literal["standard", "vip", "enterprise"]


class Customer(BaseModel):
    id: str
    name: str
    email: str
    tier: CustomerTier
    created_at: datetime
    refund_count_90d: int = 0
