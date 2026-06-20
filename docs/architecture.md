# Architecture

Customer Support Agent Desk is a deterministic local MVP of a production-style AI support workflow. The backend is FastAPI, the agent layer is organized as specialist modules, and all tool boundaries use Pydantic schemas.

```mermaid
flowchart TD
    U[Customer Message] --> UI[Support Desk UI]
    UI --> API[FastAPI API]
    API --> GR[Input Guardrails]
    GR --> TRIAGE[Triage Agent]
    TRIAGE --> FAQ[FAQ Agent]
    TRIAGE --> ORDER[Order Status Agent]
    TRIAGE --> REFUND[Refund Agent]
    TRIAGE --> TECH[Technical Support Agent]
    TRIAGE --> ESC[Escalation Agent]
    FAQ --> KB[Markdown Knowledge Base]
    ORDER --> TOOLS[Customer and Order Tools]
    REFUND --> TOOLS
    TOOLS --> DB[SQLite Demo Store]
    REFUND --> APPROVALS[Human Approval Queue]
    TECH --> KB
    ESC --> TICKETS[Ticket Tools]
    FAQ --> QA[Output Guardrails]
    ORDER --> QA
    REFUND --> QA
    TECH --> QA
    ESC --> QA
    QA --> API
    API --> LOGS[Audit Trace]
```

## Components

- `app/api/`: FastAPI routes for chat, orders, admin reset actions, tickets, approvals, traces, and evals.
- `app/agents/`: deterministic local agents for triage, FAQ, orders, refunds, technical issues, escalation, and quality review.
- `app/tools/`: typed tool functions for customers, orders, tickets, refunds, and knowledge-base search.
- `app/guardrails/`: input, tool, and output guardrails.
- `app/services/`: orchestration, RAG search, approval decisions, and audit logs.
- `app/db/`: SQLite-backed demo store seeded from JSON customers and orders.
- `data/`: seed data, policy Markdown, and labeled eval cases.
- `frontend/`: static support desk UI served by FastAPI.

## Runtime Model

The MVP intentionally avoids requiring an OpenAI key for the portfolio demo. It uses deterministic local routing and lexical retrieval so tests and evals are repeatable. `.env.example` keeps the project ready for a future OpenAI Agents SDK adapter.

The local SQLite database is created from `DATABASE_URL` and stores customers, seed orders, custom orders, tickets, approvals, refund markers, and audit traces. Database Admin can clear workflow data while keeping orders, or restore the exact JSON seed customers and orders and delete custom orders.

## Refund Guardrails

Refund safety is enforced at deterministic service and tool boundaries, not only through agent wording. A refund request must come from a verified customer, the order must belong to that customer, a pending refund approval is reused instead of duplicated, and an order with a processed refund cannot create another refund request. Damage claims for orders that are still in transit become shipping investigations rather than refund approvals.

This boundary is important for future LLM-backed agents: the model can classify intent and choose tools, but the tools still reject unsafe or duplicate state transitions. Customer identity should be bound from authenticated runtime context when exposing refund tools to an LLM, not trusted from model-generated text.
