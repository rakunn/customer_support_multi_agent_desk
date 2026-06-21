from fastapi import APIRouter

from evals.metrics import EvalReport
from evals.run_evals import run_evaluations_async

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.post("/run", response_model=EvalReport)
async def run_eval_report() -> EvalReport:
    return await run_evaluations_async()
