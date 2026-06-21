from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.seed import demo_store
from app.schemas.agent_outputs import ChatResponse
from app.services.agent_runner import run_support_turn, run_support_turn_async
from evals.metrics import EvalCase, EvalReport

EVAL_CASES_PATH = ROOT / "data" / "eval_cases.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "latest_eval_report.json"


def load_eval_cases(path: Path = EVAL_CASES_PATH) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(EvalCase.model_validate_json(line))
    return cases


def _ratio(passed: int, total: int) -> float:
    if total == 0:
        return 1.0
    return round(passed / total, 3)


@dataclass
class EvalCounters:
    routing_passed: int = 0
    specialist_passed: int = 0
    required_tools_passed: int = 0
    refund_cases: int = 0
    refund_passed: int = 0
    guardrail_cases: int = 0
    guardrail_passed: int = 0
    unsupported_refund_promises: int = 0


def _score_response(case: EvalCase, response: ChatResponse, counters: EvalCounters) -> None:
    if response.intent == case.expected_intent:
        counters.routing_passed += 1
    if response.agent == case.expected_agent:
        counters.specialist_passed += 1
    if set(case.expected_tools).issubset(set(response.tool_calls)):
        counters.required_tools_passed += 1
    if case.expected_guardrail is not None:
        counters.guardrail_cases += 1
        if response.status == "blocked" and response.intent == case.expected_intent:
            counters.guardrail_passed += 1
    if case.expected_approval_required is not None:
        counters.refund_cases += 1
        approval_required = response.approval_request_id is not None
        if approval_required == case.expected_approval_required:
            counters.refund_passed += 1
    if "refund has been issued" in response.message.lower():
        counters.unsupported_refund_promises += 1


def _build_report(cases: list[EvalCase], counters: EvalCounters) -> EvalReport:
    return EvalReport(
        total_cases=len(cases),
        routing_accuracy=_ratio(counters.routing_passed, len(cases)),
        specialist_accuracy=_ratio(counters.specialist_passed, len(cases)),
        required_tool_accuracy=_ratio(counters.required_tools_passed, len(cases)),
        refund_decision_accuracy=_ratio(counters.refund_passed, counters.refund_cases),
        guardrail_pass_rate=_ratio(counters.guardrail_passed, counters.guardrail_cases),
        unsupported_refund_promise_rate=_ratio(counters.unsupported_refund_promises, len(cases)),
    )


def run_evaluations(runtime: str = "local") -> EvalReport:
    snapshot = demo_store.snapshot()
    cases = load_eval_cases()
    counters = EvalCounters()

    try:
        for case in cases:
            demo_store.reset()
            response = run_support_turn(
                session_id=f"eval_{case.id}",
                customer_email=case.customer_email,
                message=case.message,
                runtime_override=runtime,
            )
            _score_response(case, response, counters)

        return _build_report(cases, counters)
    finally:
        demo_store.restore(snapshot)


async def run_evaluations_async(runtime: str = "local") -> EvalReport:
    snapshot = demo_store.snapshot()
    cases = load_eval_cases()
    counters = EvalCounters()

    try:
        for case in cases:
            demo_store.reset()
            response = await run_support_turn_async(
                session_id=f"eval_{case.id}",
                customer_email=case.customer_email,
                message=case.message,
                runtime_override=runtime,
            )
            _score_response(case, response, counters)

        return _build_report(cases, counters)
    finally:
        demo_store.restore(snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run support-agent evals.")
    parser.add_argument("--runtime", choices=["local", "openai"], default="local")
    args = parser.parse_args()

    if args.runtime == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("Skipping live OpenAI evals: OPENAI_API_KEY is not set.")
        return

    report = run_evaluations(runtime=args.runtime)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
