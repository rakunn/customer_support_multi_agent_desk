from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.seed import demo_store
from app.services.agent_runner import run_support_turn
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


def run_evaluations() -> EvalReport:
    snapshot = demo_store.snapshot()
    cases = load_eval_cases()
    routing_passed = 0
    specialist_passed = 0
    required_tools_passed = 0
    refund_cases = 0
    refund_passed = 0
    guardrail_cases = 0
    guardrail_passed = 0
    unsupported_refund_promises = 0

    try:
        for case in cases:
            demo_store.reset()
            response = run_support_turn(
                session_id=f"eval_{case.id}",
                customer_email="maya@example.com",
                message=case.message,
            )
            if response.intent == case.expected_intent:
                routing_passed += 1
            if response.agent == case.expected_agent:
                specialist_passed += 1
            if set(case.expected_tools).issubset(set(response.tool_calls)):
                required_tools_passed += 1
            if case.expected_guardrail is not None:
                guardrail_cases += 1
                if response.status == "blocked" and response.intent == case.expected_intent:
                    guardrail_passed += 1
            if case.expected_approval_required is not None:
                refund_cases += 1
                approval_required = response.approval_request_id is not None
                if approval_required == case.expected_approval_required:
                    refund_passed += 1
            if "refund has been issued" in response.message.lower():
                unsupported_refund_promises += 1

        return EvalReport(
            total_cases=len(cases),
            routing_accuracy=_ratio(routing_passed, len(cases)),
            specialist_accuracy=_ratio(specialist_passed, len(cases)),
            required_tool_accuracy=_ratio(required_tools_passed, len(cases)),
            refund_decision_accuracy=_ratio(refund_passed, refund_cases),
            guardrail_pass_rate=_ratio(guardrail_passed, guardrail_cases),
            unsupported_refund_promise_rate=_ratio(unsupported_refund_promises, len(cases)),
        )
    finally:
        demo_store.restore(snapshot)


def main() -> None:
    report = run_evaluations()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
