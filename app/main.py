from fastapi import FastAPI

app = FastAPI(
    title="Customer Support Agent Desk",
    description="Portfolio-ready multi-agent customer support workflow demo.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
