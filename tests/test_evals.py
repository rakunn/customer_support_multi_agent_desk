from evals.run_evals import load_eval_cases, run_evaluations
from fastapi.testclient import TestClient

from app.db.seed import demo_store
from app.main import app


def test_eval_cases_include_at_least_30_support_scenarios() -> None:
    cases = load_eval_cases()

    assert len(cases) >= 30


def test_eval_runner_reports_core_metrics() -> None:
    report = run_evaluations()

    assert report.total_cases >= 30
    assert report.routing_accuracy >= 0.8
    assert report.guardrail_pass_rate >= 0.9
    assert report.refund_decision_accuracy >= 0.8


def test_eval_api_runs_report() -> None:
    client = TestClient(app)

    response = client.post("/api/evals/run")

    assert response.status_code == 200
    assert response.json()["total_cases"] >= 30


def test_eval_api_preserves_current_demo_state() -> None:
    demo_store.reset()
    client = TestClient(app)
    chat_response = client.post(
        "/api/chat",
        json={
            "session_id": "session_before_eval",
            "customer_email": "maya@example.com",
            "message": "I want a refund for order #1005. It arrived damaged.",
        },
    )
    approval_id = chat_response.json()["approval_request_id"]

    response = client.post("/api/evals/run")

    assert response.status_code == 200
    assert approval_id in demo_store.approvals
    assert demo_store.approvals[approval_id].status == "pending"
