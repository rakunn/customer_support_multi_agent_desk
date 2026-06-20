from app.db.seed import demo_store
from app.services.agent_runner import run_support_turn
from app.tools.kb_tools import search_knowledge_base


def setup_function() -> None:
    demo_store.reset()


def test_search_knowledge_base_returns_policy_citation() -> None:
    results = search_knowledge_base("opened items return policy", top_k=3)

    assert results
    assert results[0].policy_id == "RETURN-OPENED"
    assert "opened" in results[0].content.lower()


def test_faq_agent_uses_knowledge_base_with_policy_id() -> None:
    response = run_support_turn(
        session_id="session_policy",
        customer_email="maya@example.com",
        message="What is your return policy for opened items?",
    )

    assert response.agent == "FAQ Agent"
    assert response.intent == "faq_policy_question"
    assert "RETURN-OPENED" in response.message
    assert "search_knowledge_base" in response.tool_calls


def test_unknown_policy_question_gets_safe_uncertain_response() -> None:
    response = run_support_turn(
        session_id="session_unknown_policy",
        customer_email="maya@example.com",
        message="What is the policy for teleporting my package to the moon?",
    )

    assert response.agent == "FAQ Agent"
    assert "cannot confirm" in response.message.lower()

