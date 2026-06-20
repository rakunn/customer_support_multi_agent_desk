from pydantic import BaseModel, Field


class KnowledgeBaseResult(BaseModel):
    policy_id: str
    title: str
    heading: str
    content: str
    score: float = Field(ge=0)
    source_path: str

