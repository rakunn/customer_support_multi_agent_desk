from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents import Agent, RunConfig, RunContextWrapper, Runner, function_tool
from agents.memory import SQLiteSession

from app.config import Settings
from app.db.seed import demo_store
from app.guardrails.output_guardrails import review_output
from app.schemas.agent_outputs import ChatResponse, ToolError
from app.services.audit_service import log_agent_event
from app.tools.customer_tools import list_customer_orders, lookup_customer
from app.tools.kb_tools import search_knowledge_base
from app.tools.order_tools import lookup_order
from app.tools.refund_tools import check_refund_eligibility
from app.tools.refund_tools import create_refund_approval_request as create_refund_approval
from app.tools.ticket_tools import create_ticket, update_ticket


@dataclass
class OpenAISupportContext:
    session_id: str
    customer_email: str | None
    tool_calls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OpenAISupportAgents:
    triage_agent: Agent[OpenAISupportContext]
    faq_agent: Agent[OpenAISupportContext]
    order_agent: Agent[OpenAISupportContext]
    refund_agent: Agent[OpenAISupportContext]
    technical_agent: Agent[OpenAISupportContext]
    escalation_agent: Agent[OpenAISupportContext]


def _record_tool(ctx: RunContextWrapper[OpenAISupportContext], name: str) -> None:
    if name not in ctx.context.tool_calls:
        ctx.context.tool_calls.append(name)


def _lookup_verified_customer(ctx: RunContextWrapper[OpenAISupportContext]) -> Any:
    customer_email = ctx.context.customer_email
    if not customer_email:
        return ToolError(
            code="customer_not_verified",
            message="No verified customer email is attached to this chat request.",
        )
    return lookup_customer(customer_email)


def lookup_customer_for_model(ctx: RunContextWrapper[OpenAISupportContext]) -> Any:
    """Look up the customer bound to the current chat request."""
    _record_tool(ctx, "lookup_customer")
    return _lookup_verified_customer(ctx)


def list_customer_orders_for_model(ctx: RunContextWrapper[OpenAISupportContext]) -> Any:
    """List orders for the customer bound to the current chat request."""
    _record_tool(ctx, "list_customer_orders")
    customer = _lookup_verified_customer(ctx)
    if isinstance(customer, ToolError):
        return customer
    return list_customer_orders(customer.id)


def lookup_order_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    order_id: str,
) -> Any:
    """Look up an order by order ID."""
    _record_tool(ctx, "lookup_order")
    return lookup_order(order_id)


def search_knowledge_base_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    query: str,
    top_k: int = 3,
) -> Any:
    """Search local support policy and troubleshooting articles."""
    _record_tool(ctx, "search_knowledge_base")
    return search_knowledge_base(query=query, top_k=top_k)


def create_ticket_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    issue_type: str,
    summary: str,
    priority: str,
) -> Any:
    """Create a support ticket for the verified customer when available."""
    _record_tool(ctx, "create_ticket")
    customer = _lookup_verified_customer(ctx)
    customer_id = None if isinstance(customer, ToolError) else customer.id
    return create_ticket(customer_id, issue_type, summary, priority)


def update_ticket_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    ticket_id: str,
    status: str,
    note: str,
) -> Any:
    """Update an existing support ticket."""
    _record_tool(ctx, "update_ticket")
    return update_ticket(ticket_id=ticket_id, status=status, note=note)


def check_refund_eligibility_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    order_id: str,
    reason: str,
) -> Any:
    """Check whether an order is eligible for a refund under demo policy."""
    _record_tool(ctx, "check_refund_eligibility")
    return check_refund_eligibility(order_id=order_id, reason=reason)


def create_refund_approval_request_for_model(
    ctx: RunContextWrapper[OpenAISupportContext],
    order_id: str,
    reason: str,
    amount: float,
    ticket_id: str | None = None,
) -> Any:
    """Create a human approval request for a refund for the verified customer."""
    _record_tool(ctx, "create_refund_approval_request")
    customer = _lookup_verified_customer(ctx)
    if isinstance(customer, ToolError):
        return customer
    return create_refund_approval(
        order_id=order_id,
        customer_id=customer.id,
        reason=reason,
        amount=amount,
        ticket_id=ticket_id,
    )


lookup_customer_tool = function_tool(
    lookup_customer_for_model,
    name_override="lookup_customer",
)
list_customer_orders_tool = function_tool(
    list_customer_orders_for_model,
    name_override="list_customer_orders",
)
lookup_order_tool = function_tool(lookup_order_for_model, name_override="lookup_order")
search_knowledge_base_tool = function_tool(
    search_knowledge_base_for_model,
    name_override="search_knowledge_base",
)
create_ticket_tool = function_tool(create_ticket_for_model, name_override="create_ticket")
update_ticket_tool = function_tool(update_ticket_for_model, name_override="update_ticket")
check_refund_eligibility_tool = function_tool(
    check_refund_eligibility_for_model,
    name_override="check_refund_eligibility",
)
create_refund_approval_request_tool = function_tool(
    create_refund_approval_request_for_model,
    name_override="create_refund_approval_request",
)


BASE_RESPONSE_INSTRUCTIONS = """
Return a structured ChatResponse. Keep messages concise and customer-safe.
Do not expose internal data. Never say a refund has been issued or processed
unless the tool call list includes issue_mock_refund, which is not available in
this chat runtime. Use the verified customer context supplied by tools; do not
ask the model to choose a customer_id.
"""


def build_support_agents(model: str) -> OpenAISupportAgents:
    faq_agent = Agent[OpenAISupportContext](
        name="FAQ Agent",
        handoff_description="Policy, FAQ, shipping, warranty, returns, and knowledge-base questions.",
        model=model,
        instructions=(
            "Answer policy and FAQ questions using search_knowledge_base. "
            "Create a ticket for the interaction. "
            "Set intent to faq_policy_question and agent to FAQ Agent. "
            + BASE_RESPONSE_INSTRUCTIONS
        ),
        tools=[lookup_customer_tool, search_knowledge_base_tool, create_ticket_tool],
        output_type=ChatResponse,
    )
    order_agent = Agent[OpenAISupportContext](
        name="Order Status Agent",
        handoff_description="Order tracking, delivery status, shipment delays, and package questions.",
        model=model,
        instructions=(
            "Use lookup_customer, lookup_order, list_customer_orders when useful, "
            "and create_ticket for order-status support work. "
            "Set intent to order_status and agent to Order Status Agent. "
            + BASE_RESPONSE_INSTRUCTIONS
        ),
        tools=[
            lookup_customer_tool,
            lookup_order_tool,
            list_customer_orders_tool,
            create_ticket_tool,
        ],
        output_type=ChatResponse,
    )
    refund_agent = Agent[OpenAISupportContext](
        name="Refund Agent",
        handoff_description="Refund, return, damaged item, chargeback, and money-back requests.",
        model=model,
        instructions=(
            "Use lookup_customer, lookup_order, check_refund_eligibility, create_ticket, "
            "create_refund_approval_request, and update_ticket as needed. "
            "Refund approvals are human-in-the-loop: create approval requests but do not "
            "claim refunds are issued. Set intent to refund_request and agent to Refund Agent. "
            + BASE_RESPONSE_INSTRUCTIONS
        ),
        tools=[
            lookup_customer_tool,
            lookup_order_tool,
            check_refund_eligibility_tool,
            create_ticket_tool,
            create_refund_approval_request_tool,
            update_ticket_tool,
        ],
        output_type=ChatResponse,
    )
    technical_agent = Agent[OpenAISupportContext](
        name="Technical Support Agent",
        handoff_description="Technical problems, CSV uploads, password reset, bugs, and integrations.",
        model=model,
        instructions=(
            "Troubleshoot technical issues, use the knowledge base where useful, "
            "and create a support ticket. Set intent to technical_issue and agent "
            "to Technical Support Agent. " + BASE_RESPONSE_INSTRUCTIONS
        ),
        tools=[lookup_customer_tool, search_knowledge_base_tool, create_ticket_tool],
        output_type=ChatResponse,
    )
    escalation_agent = Agent[OpenAISupportContext](
        name="Escalation Agent",
        handoff_description="Requests for a human, manager, representative, or escalation.",
        model=model,
        instructions=(
            "Prepare a concise human handoff summary, create a ticket, and update it "
            "to escalated. Set intent to human_escalation and agent to Escalation Agent. "
            + BASE_RESPONSE_INSTRUCTIONS
        ),
        tools=[lookup_customer_tool, create_ticket_tool, update_ticket_tool],
        output_type=ChatResponse,
    )
    triage_agent = Agent[OpenAISupportContext](
        name="Triage Agent",
        model=model,
        instructions=(
            "Route each customer support request to the best specialist. "
            "Use handoffs instead of answering directly unless the request is clearly "
            "outside support scope. " + BASE_RESPONSE_INSTRUCTIONS
        ),
        handoffs=[faq_agent, order_agent, refund_agent, technical_agent, escalation_agent],
        output_type=ChatResponse,
    )
    return OpenAISupportAgents(
        triage_agent=triage_agent,
        faq_agent=faq_agent,
        order_agent=order_agent,
        refund_agent=refund_agent,
        technical_agent=technical_agent,
        escalation_agent=escalation_agent,
    )


async def run_openai_support_turn(
    session_id: str,
    customer_email: str | None,
    message: str,
    settings: Settings,
) -> ChatResponse:
    context = OpenAISupportContext(session_id=session_id, customer_email=customer_email)
    support_agents = build_support_agents(model=settings.openai_model)
    sdk_session = SQLiteSession(
        session_id=session_id,
        db_path=demo_store.db_path,
    )
    run_config = RunConfig(
        model=settings.openai_model,
        tracing_disabled=not settings.enable_agent_tracing,
        workflow_name="Customer Support Agent Desk",
        group_id=session_id,
    )

    try:
        result = await Runner.run(
            support_agents.triage_agent,
            message,
            context=context,
            max_turns=8,
            run_config=run_config,
            session=sdk_session,
        )
    except Exception as exc:
        log_agent_event(
            session_id=session_id,
            agent_name="OpenAI Runtime",
            event_type="sdk_error",
            payload={"error": str(exc), "model": settings.openai_model},
        )
        return ChatResponse(
            ticket_id=None,
            agent="OpenAI Runtime",
            intent="runtime_error",
            status="error",
            message=(
                "The live OpenAI runtime could not complete this request. "
                "Please check the OpenAI configuration and trace logs."
            ),
            tool_calls=[],
        )

    response = _coerce_chat_response(result.final_output, result.last_agent.name)
    tool_calls = _merge_tool_calls(
        context.tool_calls,
        _extract_tool_calls_from_result(result),
        response.tool_calls,
    )
    response = response.model_copy(update={"tool_calls": tool_calls})
    review = review_output(
        message=response.message,
        tool_calls=response.tool_calls,
        approval_request_id=response.approval_request_id,
    )
    if not review.allowed:
        response = response.model_copy(update={"message": review.safe_message})

    log_agent_event(
        session_id=session_id,
        agent_name=response.agent,
        event_type="openai_response",
        payload={
            "last_agent": result.last_agent.name,
            "tool_calls": response.tool_calls,
            "final_output": response.model_dump(),
        },
    )
    return response


def _coerce_chat_response(final_output: Any, last_agent_name: str) -> ChatResponse:
    if isinstance(final_output, ChatResponse):
        return final_output
    if isinstance(final_output, dict):
        return ChatResponse.model_validate(final_output)
    return ChatResponse(
        ticket_id=None,
        agent=last_agent_name,
        intent="support_request",
        status="open",
        message=str(final_output),
        tool_calls=[],
    )


def _extract_tool_calls_from_result(result: Any) -> list[str]:
    names: list[str] = []
    for item in getattr(result, "new_items", []):
        if getattr(item, "type", None) != "tool_call_item":
            continue
        tool_name = getattr(item, "tool_name", None)
        if tool_name:
            names.append(tool_name)
    return names


def _merge_tool_calls(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for name in group:
            if name not in merged:
                merged.append(name)
    return merged
