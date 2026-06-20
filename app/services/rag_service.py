from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas.kb import KnowledgeBaseResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = PROJECT_ROOT / "data" / "kb"

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "for",
    "from",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "policy",
    "the",
    "to",
    "what",
    "when",
    "your",
}


@dataclass(frozen=True)
class KnowledgeBaseChunk:
    policy_id: str
    title: str
    heading: str
    content: str
    source_path: str

    @property
    def searchable_text(self) -> str:
        return f"{self.policy_id} {self.title} {self.heading} {self.content}".lower()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def _parse_policy_file(path: Path) -> list[KnowledgeBaseChunk]:
    title = path.stem.replace("_", " ").title()
    chunks: list[KnowledgeBaseChunk] = []
    current_heading = ""
    current_policy_id = path.stem.upper()
    current_lines: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            title = line.removeprefix("# ").strip()
            continue
        if line.startswith("## "):
            if current_lines:
                chunks.append(
                    KnowledgeBaseChunk(
                        policy_id=current_policy_id,
                        title=title,
                        heading=current_heading,
                        content=" ".join(current_lines).strip(),
                        source_path=str(path.relative_to(PROJECT_ROOT)),
                    )
                )
            heading_text = line.removeprefix("## ").strip()
            if ":" in heading_text:
                current_policy_id, current_heading = [part.strip() for part in heading_text.split(":", 1)]
            else:
                current_policy_id = heading_text.upper().replace(" ", "-")
                current_heading = heading_text
            current_lines = []
            continue
        if line.strip():
            current_lines.append(line.strip())

    if current_lines:
        chunks.append(
            KnowledgeBaseChunk(
                policy_id=current_policy_id,
                title=title,
                heading=current_heading,
                content=" ".join(current_lines).strip(),
                source_path=str(path.relative_to(PROJECT_ROOT)),
            )
        )
    return chunks


@lru_cache
def load_knowledge_base() -> list[KnowledgeBaseChunk]:
    chunks: list[KnowledgeBaseChunk] = []
    for path in sorted(KB_DIR.glob("*.md")):
        chunks.extend(_parse_policy_file(path))
    return chunks


def search_policy_chunks(query: str, top_k: int = 5) -> list[KnowledgeBaseResult]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    scored: list[KnowledgeBaseResult] = []
    for chunk in load_knowledge_base():
        chunk_tokens = _tokens(chunk.searchable_text)
        overlap = query_tokens.intersection(chunk_tokens)
        if not overlap:
            continue
        score = len(overlap) / len(query_tokens)
        if score < 0.34:
            continue
        scored.append(
            KnowledgeBaseResult(
                policy_id=chunk.policy_id,
                title=chunk.title,
                heading=chunk.heading,
                content=chunk.content,
                score=round(score, 3),
                source_path=chunk.source_path,
            )
        )

    return sorted(scored, key=lambda result: result.score, reverse=True)[:top_k]

