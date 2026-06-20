# Customer Support Agent Desk

Customer Support Agent Desk is a portfolio-ready multi-agent support workflow demo. It routes customer messages to specialist agents, uses typed tools over customer and order data, retrieves local policy documents, creates human approval requests for risky refunds, applies guardrails, logs traces, and measures behavior with eval cases.

## What It Demonstrates

- Triage and specialist handoffs for FAQ, order, refund, technical, and escalation flows
- Tool use against customer, order, ticket, approval, and knowledge-base data
- Human-in-the-loop approval for refund workflows
- Input, tool, and output guardrails for support safety
- Audit traces and evaluation metrics for agent behavior
- A support-desk UI for chat, tickets, approvals, and traces

## Quick Start

```bash
source .venv/bin/activate
make test
make dev
```

Open `http://127.0.0.1:8000/docs` for the API and `http://127.0.0.1:8000/` for the support desk UI once the UI milestone is present.

## Environment

Copy `.env.example` to `.env` for local development. The MVP runs with deterministic local agents and mock data without an OpenAI key; the environment keeps the project ready for a live OpenAI Agents SDK adapter.

## Core Commands

```bash
make dev
make test
make eval
make seed
make index-kb
```

## Current Scope

The source-of-truth implementation roadmap is in `customer_support_agent_desk_implementation_plan.md`. This repository implements it as a local deterministic MVP first so portfolio reviewers can run and evaluate the workflows without external services.

