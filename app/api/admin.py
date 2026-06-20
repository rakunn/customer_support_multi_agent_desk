from fastapi import APIRouter

from app.db.seed import demo_store
from app.schemas.admin import AdminActionResult, AdminStats

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats() -> AdminStats:
    return AdminStats.model_validate(demo_store.stats())


@router.post("/reset", response_model=AdminActionResult)
async def reset() -> AdminActionResult:
    demo_store.reset()
    return AdminActionResult(status="reset", stats=AdminStats.model_validate(demo_store.stats()))


@router.post("/purge-workflow", response_model=AdminActionResult)
async def purge_workflow() -> AdminActionResult:
    demo_store.purge_workflow()
    return AdminActionResult(status="purged", stats=AdminStats.model_validate(demo_store.stats()))

