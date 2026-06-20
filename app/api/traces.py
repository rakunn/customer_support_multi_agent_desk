from typing import Any

from fastapi import APIRouter

from app.services.audit_service import list_agent_events

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("", response_model=list[dict[str, Any]])
async def traces() -> list[dict[str, Any]]:
    return list_agent_events()

