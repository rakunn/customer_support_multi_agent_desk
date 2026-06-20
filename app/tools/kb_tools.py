from app.schemas.kb import KnowledgeBaseResult
from app.services.rag_service import search_policy_chunks


def search_knowledge_base(query: str, top_k: int = 5) -> list[KnowledgeBaseResult]:
    return search_policy_chunks(query=query, top_k=top_k)
