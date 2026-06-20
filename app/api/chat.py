from fastapi import APIRouter

from app.schemas.agent_outputs import ChatRequest, ChatResponse
from app.services.agent_runner import run_support_turn

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return run_support_turn(
        session_id=request.session_id,
        customer_email=request.customer_email,
        message=request.message,
    )

