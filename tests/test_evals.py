from evals.run_evals import load_eval_cases, run_evaluations


def test_eval_cases_include_at_least_30_support_scenarios() -> None:
    cases = load_eval_cases()

    assert len(cases) >= 30


def test_eval_runner_reports_core_metrics() -> None:
    report = run_evaluations()

    assert report.total_cases >= 30
    assert report.routing_accuracy >= 0.8
    assert report.guardrail_pass_rate >= 0.9
    assert report.refund_decision_accuracy >= 0.8
