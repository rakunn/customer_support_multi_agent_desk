from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    ok: Literal[False] = False
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    name: str
    ok: bool
    summary: str

