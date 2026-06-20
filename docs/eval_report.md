# Evaluation Report

Latest local run:

```bash
.venv/bin/python evals/run_evals.py
```

| Metric | Result |
|---|---:|
| Total labeled cases | 30 |
| Intent routing accuracy | 100% |
| Specialist handoff accuracy | 100% |
| Required tool call accuracy | 100% |
| Refund decision accuracy | 100% |
| Guardrail pass rate | 100% |
| Unsupported refund promise rate | 0% |

The eval suite covers order status, refund decisions, FAQ policy retrieval, technical support routing, escalation, prompt injection, off-topic requests, and privacy-sensitive requests.

