from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(
    title="Customer Support Agent Desk",
    description="Portfolio-ready multi-agent customer support workflow demo.",
    version="0.1.0",
)

app.include_router(chat_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
