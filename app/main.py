from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.approvals import router as approvals_router
from app.api.chat import router as chat_router
from app.api.evals import router as evals_router
from app.api.tickets import router as tickets_router
from app.api.traces import router as traces_router

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Customer Support Agent Desk",
    description="Portfolio-ready multi-agent customer support workflow demo.",
    version="0.1.0",
)

app.include_router(chat_router)
app.include_router(approvals_router)
app.include_router(evals_router)
app.include_router(tickets_router)
app.include_router(traces_router)

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/", tags=["ui"])
async def support_desk() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
