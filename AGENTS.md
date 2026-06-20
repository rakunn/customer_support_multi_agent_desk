# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains a minimal FastAPI entry point in `main.py`, HTTP smoke checks in `test_main.http`, and the roadmap in `customer_support_agent_desk_implementation_plan.md`. Follow that plan as the source of truth while expanding the project.

Target structure:
- `app/`: backend source, including `api/`, `agents/`, `tools/`, `guardrails/`, `schemas/`, `services/`, and `db/`.
- `tests/`: pytest coverage for tools, guardrails, routing, and refund workflows.
- `data/`: seed customers, orders, knowledge-base Markdown, and `eval_cases.jsonl`.
- `evals/`: evaluation runner, metrics, and reports.
- `frontend/`: planned support-desk UI.
- `docs/`: architecture, screenshots, demo script, and evaluation report.

## Build, Test, and Development Commands

- `source .venv/bin/activate`: activate the local virtual environment.
- `uvicorn main:app --reload`: run the current FastAPI stub locally.
- `uv run uvicorn app.main:app --reload`: planned backend command after moving into `app/`.
- `uv run pytest`: run the pytest suite once tests are added.
- `uv run python scripts/seed_db.py`: planned seed-data setup.
- `uv run python scripts/index_kb.py`: planned knowledge-base indexing.
- `uv run python evals/run_evals.py`: planned routing, guardrail, and refund-policy evaluation.

## Coding Style & Naming Conventions

Use Python 3.11+, 4-space indentation, type hints, and Pydantic models for API/tool boundaries. Use `snake_case` for functions, modules, and tool names; `PascalCase` for classes and schemas. Name specialist agent modules like `refund_agent.py` and tool modules like `order_tools.py`. Keep FastAPI routes thin; put orchestration in `services/` and business rules in tools or guardrails.

## Testing Guidelines

Use pytest. Name files `test_*.py` and test functions `test_*`. Cover tool behavior, safe structured errors, triage routing, approval requirements, prompt-injection handling, and output guardrails. Add eval cases in `data/eval_cases.jsonl` for expected intent, specialist agent, tool calls, and guardrail outcomes.

## Commit & Pull Request Guidelines

This repository has no committed history yet, so use Conventional Commits going forward, for example `feat: add refund approval workflow` or `test: cover prompt injection guardrail`. Pull requests should include a short summary, linked issue if available, commands run, screenshots for UI changes, and updated eval results when agent behavior changes.

## Security & Configuration Tips

Do not commit `.env`, API keys, local databases, vector indexes, or trace logs. Maintain `.env.example` with `OPENAI_API_KEY`, `DATABASE_URL`, `VECTOR_DB_DIR`, refund limits, tracing flags, and mock-refund settings.
