from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.customer import Customer
from app.schemas.order import Order
from app.schemas.refund import ApprovalRequest
from app.schemas.ticket import Ticket

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list in {path}")
    return payload


class DemoStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.customers = {
            customer.id: customer
            for customer in (
                Customer.model_validate(item)
                for item in _load_json(DATA_DIR / "seed_customers.json")
            )
        }
        self.orders = {
            order.id: order
            for order in (
                Order.model_validate(item)
                for item in _load_json(DATA_DIR / "seed_orders.json")
            )
        }
        self.tickets: dict[str, Ticket] = {}
        self.approvals: dict[str, ApprovalRequest] = {}
        self.agent_events: list[dict[str, Any]] = []
        self.refunded_approval_ids: set[str] = set()
        self._ticket_counter = 1
        self._approval_counter = 1

    def next_ticket_id(self) -> str:
        ticket_id = f"ticket_{self._ticket_counter:04d}"
        self._ticket_counter += 1
        return ticket_id

    def next_approval_id(self) -> str:
        approval_id = f"approval_{self._approval_counter:04d}"
        self._approval_counter += 1
        return approval_id


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


demo_store = DemoStore()
