from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas.conversation import ConversationState
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
        self.db_path = self._resolve_database_path()
        self._init_schema()
        self.seed_if_empty()

    def _resolve_database_path(self) -> Path:
        database_url = get_settings().database_url
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if database_url.startswith(prefix):
                raw_path = database_url.removeprefix(prefix)
                path = Path(raw_path)
                if not path.is_absolute():
                    path = PROJECT_ROOT / path
                return path
        return PROJECT_ROOT / "support_desk.db"

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists customers (
                    id text primary key,
                    payload text not null
                );
                create table if not exists orders (
                    id text primary key,
                    customer_id text not null,
                    is_seed integer not null default 0,
                    payload text not null
                );
                create table if not exists tickets (
                    id text primary key,
                    payload text not null
                );
                create table if not exists approvals (
                    id text primary key,
                    payload text not null
                );
                create table if not exists agent_events (
                    id integer primary key autoincrement,
                    payload text not null
                );
                create table if not exists refunded_approvals (
                    approval_id text primary key
                );
                create table if not exists refunded_orders (
                    order_id text primary key,
                    approval_id text not null,
                    processed_at text not null
                );
                create table if not exists conversation_states (
                    session_id text primary key,
                    payload text not null
                );
                """
            )

    def seed_if_empty(self) -> None:
        with self._connect() as connection:
            customer_count = connection.execute("select count(*) from customers").fetchone()[0]
            order_count = connection.execute("select count(*) from orders").fetchone()[0]
        if customer_count == 0 and order_count == 0:
            self.reset()

    def reset(self) -> None:
        customers = [Customer.model_validate(item) for item in _load_json(DATA_DIR / "seed_customers.json")]
        orders = [Order.model_validate(item) for item in _load_json(DATA_DIR / "seed_orders.json")]
        with self._connect() as connection:
            connection.execute("delete from refunded_orders")
            connection.execute("delete from refunded_approvals")
            connection.execute("delete from agent_events")
            connection.execute("delete from conversation_states")
            connection.execute("delete from approvals")
            connection.execute("delete from tickets")
            connection.execute("delete from orders")
            connection.execute("delete from customers")
            connection.executemany(
                "insert into customers (id, payload) values (?, ?)",
                [(customer.id, customer.model_dump_json()) for customer in customers],
            )
            connection.executemany(
                "insert into orders (id, customer_id, is_seed, payload) values (?, ?, 1, ?)",
                [(order.id, order.customer_id, order.model_dump_json()) for order in orders],
            )

    def next_ticket_id(self) -> str:
        existing_ids = self.tickets.keys()
        max_id = self._max_numeric_suffix(existing_ids, "ticket_")
        return f"ticket_{max_id + 1:04d}"

    def next_approval_id(self) -> str:
        existing_ids = self.approvals.keys()
        max_id = self._max_numeric_suffix(existing_ids, "approval_")
        return f"approval_{max_id + 1:04d}"

    @staticmethod
    def _max_numeric_suffix(values: Any, prefix: str) -> int:
        max_id = 0
        for value in values:
            if str(value).startswith(prefix):
                suffix = str(value).removeprefix(prefix)
                if suffix.isdigit():
                    max_id = max(max_id, int(suffix))
        return max_id

    @property
    def customers(self) -> dict[str, Customer]:
        with self._connect() as connection:
            rows = connection.execute("select payload from customers").fetchall()
        return {
            customer.id: customer
            for customer in (Customer.model_validate_json(row["payload"]) for row in rows)
        }

    @property
    def orders(self) -> dict[str, Order]:
        with self._connect() as connection:
            rows = connection.execute("select payload from orders").fetchall()
        return {
            order.id: order
            for order in (Order.model_validate_json(row["payload"]) for row in rows)
        }

    @property
    def tickets(self) -> dict[str, Ticket]:
        with self._connect() as connection:
            rows = connection.execute("select payload from tickets").fetchall()
        return {
            ticket.id: ticket
            for ticket in (Ticket.model_validate_json(row["payload"]) for row in rows)
        }

    @property
    def approvals(self) -> dict[str, ApprovalRequest]:
        with self._connect() as connection:
            rows = connection.execute("select payload from approvals").fetchall()
        return {
            approval.id: approval
            for approval in (ApprovalRequest.model_validate_json(row["payload"]) for row in rows)
        }

    @property
    def agent_events(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("select payload from agent_events order by id").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    @property
    def refunded_approval_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute("select approval_id from refunded_approvals").fetchall()
        return {row["approval_id"] for row in rows}

    @property
    def refunded_order_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute("select order_id from refunded_orders").fetchall()
        return {row["order_id"] for row in rows}

    def is_order_refunded(self, order_id: str) -> bool:
        normalized_order_id = order_id.strip().removeprefix("#")
        with self._connect() as connection:
            row = connection.execute(
                "select 1 from refunded_orders where order_id = ?",
                (normalized_order_id,),
            ).fetchone()
        return row is not None

    def find_refund_approval(
        self,
        order_id: str,
        statuses: set[str] | None = None,
    ) -> ApprovalRequest | None:
        normalized_order_id = order_id.strip().removeprefix("#")
        approvals = [
            approval
            for approval in self.approvals.values()
            if approval.order_id == normalized_order_id
            and approval.action_type == "refund"
            and (statuses is None or approval.status in statuses)
        ]
        if not approvals:
            return None
        return sorted(approvals, key=lambda approval: approval.created_at)[0]

    def save_order(self, order: Order, is_seed: bool = False) -> Order:
        with self._connect() as connection:
            connection.execute(
                """
                insert into orders (id, customer_id, is_seed, payload)
                values (?, ?, ?, ?)
                on conflict(id) do update set
                    customer_id = excluded.customer_id,
                    is_seed = excluded.is_seed,
                    payload = excluded.payload
                """,
                (order.id, order.customer_id, int(is_seed), order.model_dump_json()),
            )
        return order

    def is_seed_order(self, order_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "select is_seed from orders where id = ?",
                (order_id,),
            ).fetchone()
        return bool(row and row["is_seed"])

    def delete_custom_order(self, order_id: str) -> bool:
        if self.is_seed_order(order_id):
            return False
        with self._connect() as connection:
            cursor = connection.execute("delete from orders where id = ? and is_seed = 0", (order_id,))
        return cursor.rowcount > 0

    def save_ticket(self, ticket: Ticket) -> Ticket:
        with self._connect() as connection:
            connection.execute(
                """
                insert into tickets (id, payload) values (?, ?)
                on conflict(id) do update set payload = excluded.payload
                """,
                (ticket.id, ticket.model_dump_json()),
            )
        return ticket

    def save_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self._connect() as connection:
            connection.execute(
                """
                insert into approvals (id, payload) values (?, ?)
                on conflict(id) do update set payload = excluded.payload
                """,
                (approval.id, approval.model_dump_json()),
            )
        return approval

    def add_agent_event(self, event: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("insert into agent_events (payload) values (?)", (json.dumps(event),))

    def get_conversation_state(self, session_id: str) -> ConversationState | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from conversation_states where session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return ConversationState.model_validate_json(row["payload"])

    def save_conversation_state(self, state: ConversationState) -> ConversationState:
        with self._connect() as connection:
            connection.execute(
                """
                insert into conversation_states (session_id, payload) values (?, ?)
                on conflict(session_id) do update set payload = excluded.payload
                """,
                (state.session_id, state.model_dump_json()),
            )
        return state

    def mark_refunded(self, approval_id: str, order_id: str) -> None:
        processed_at = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                "insert or ignore into refunded_approvals (approval_id) values (?)",
                (approval_id,),
            )
            connection.execute(
                """
                insert or ignore into refunded_orders (order_id, approval_id, processed_at)
                values (?, ?, ?)
                """,
                (order_id, approval_id, processed_at),
            )

    def purge_workflow(self) -> None:
        with self._connect() as connection:
            connection.execute("delete from refunded_orders")
            connection.execute("delete from refunded_approvals")
            connection.execute("delete from agent_events")
            connection.execute("delete from conversation_states")
            connection.execute("delete from approvals")
            connection.execute("delete from tickets")

    def stats(self) -> dict[str, int]:
        with self._connect() as connection:
            return {
                "customers": connection.execute("select count(*) from customers").fetchone()[0],
                "orders": connection.execute("select count(*) from orders").fetchone()[0],
                "custom_orders": connection.execute("select count(*) from orders where is_seed = 0").fetchone()[0],
                "tickets": connection.execute("select count(*) from tickets").fetchone()[0],
                "approvals": connection.execute("select count(*) from approvals").fetchone()[0],
                "traces": connection.execute("select count(*) from agent_events").fetchone()[0],
            }

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as connection:
            return {
                "customers": [dict(row) for row in connection.execute("select * from customers").fetchall()],
                "orders": [dict(row) for row in connection.execute("select * from orders").fetchall()],
                "tickets": [dict(row) for row in connection.execute("select * from tickets").fetchall()],
                "approvals": [dict(row) for row in connection.execute("select * from approvals").fetchall()],
                "agent_events": [dict(row) for row in connection.execute("select * from agent_events").fetchall()],
                "conversation_states": [
                    dict(row) for row in connection.execute("select * from conversation_states").fetchall()
                ],
                "refunded_approvals": [
                    dict(row) for row in connection.execute("select * from refunded_approvals").fetchall()
                ],
                "refunded_orders": [
                    dict(row) for row in connection.execute("select * from refunded_orders").fetchall()
                ],
            }

    def restore(self, snapshot: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("delete from refunded_orders")
            connection.execute("delete from refunded_approvals")
            connection.execute("delete from agent_events")
            connection.execute("delete from conversation_states")
            connection.execute("delete from approvals")
            connection.execute("delete from tickets")
            connection.execute("delete from orders")
            connection.execute("delete from customers")
            connection.executemany(
                "insert into customers (id, payload) values (:id, :payload)",
                snapshot["customers"],
            )
            connection.executemany(
                "insert into orders (id, customer_id, is_seed, payload) values (:id, :customer_id, :is_seed, :payload)",
                snapshot["orders"],
            )
            connection.executemany(
                "insert into tickets (id, payload) values (:id, :payload)",
                snapshot["tickets"],
            )
            connection.executemany(
                "insert into approvals (id, payload) values (:id, :payload)",
                snapshot["approvals"],
            )
            connection.executemany(
                "insert into agent_events (id, payload) values (:id, :payload)",
                snapshot["agent_events"],
            )
            connection.executemany(
                "insert into conversation_states (session_id, payload) values (:session_id, :payload)",
                snapshot.get("conversation_states", []),
            )
            connection.executemany(
                "insert into refunded_approvals (approval_id) values (:approval_id)",
                snapshot["refunded_approvals"],
            )
            connection.executemany(
                """
                insert into refunded_orders (order_id, approval_id, processed_at)
                values (:order_id, :approval_id, :processed_at)
                """,
                snapshot.get("refunded_orders", []),
            )


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


demo_store = DemoStore()
