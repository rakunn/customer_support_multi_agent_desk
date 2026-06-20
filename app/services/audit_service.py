from typing import Any

from app.db.seed import demo_store, utc_now


def log_agent_event(
    session_id: str,
    agent_name: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    demo_store.agent_events.append(
        {
            "session_id": session_id,
            "agent_name": agent_name,
            "event_type": event_type,
            "payload": payload,
            "created_at": utc_now().isoformat(),
        }
    )


def list_agent_events() -> list[dict[str, Any]]:
    return list(demo_store.agent_events)

