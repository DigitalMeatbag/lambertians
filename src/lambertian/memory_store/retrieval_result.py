"""IS-10 memory retrieval and write types."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EpisodicDocument:
    document_id: str
    content: str
    metadata: dict[str, object]  # object: heterogeneous Chroma metadata values
    similarity_score: float


@dataclass(frozen=True)
class MemoryRetrievalResult:
    documents: list[EpisodicDocument]
    retrieval_miss: bool  # True if zero docs met minimum_retrieval_score


@dataclass(frozen=True)
class MemoryWriteRequest:
    content: str
    document_type: str  # "model_response" | "tool_result" | "self_insight" | "ground_contact"
    turn_number: int
    write_index: int
    tool_name: Optional[str]
    adaptation_class: Optional[str]
