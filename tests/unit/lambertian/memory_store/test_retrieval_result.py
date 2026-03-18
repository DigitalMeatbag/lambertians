"""Tests for IS-10 retrieval result dataclasses."""
from __future__ import annotations
import pytest
from lambertian.memory_store.retrieval_result import (
    EpisodicDocument,
    MemoryRetrievalResult,
    MemoryWriteRequest,
)


class TestEpisodicDocument:
    def test_construction(self) -> None:
        doc = EpisodicDocument(
            document_id="inst-t1-0",
            content="hello world",
            metadata={"turn_number": 1},
            similarity_score=0.85,
        )
        assert doc.document_id == "inst-t1-0"
        assert doc.similarity_score == 0.85

    def test_frozen_immutability(self) -> None:
        doc = EpisodicDocument("id", "content", {}, 0.5)
        with pytest.raises(Exception):
            doc.document_id = "other"  # type: ignore[misc]


class TestMemoryRetrievalResult:
    def test_retrieval_miss_true_when_empty(self) -> None:
        result = MemoryRetrievalResult(documents=[], retrieval_miss=True)
        assert result.retrieval_miss is True
        assert result.documents == []

    def test_frozen(self) -> None:
        result = MemoryRetrievalResult(documents=[], retrieval_miss=False)
        with pytest.raises(Exception):
            result.retrieval_miss = True  # type: ignore[misc]


class TestMemoryWriteRequest:
    def test_construction_with_optionals_none(self) -> None:
        req = MemoryWriteRequest(
            content="some content",
            document_type="model_response",
            turn_number=5,
            write_index=0,
            tool_name=None,
            adaptation_class=None,
        )
        assert req.turn_number == 5
        assert req.tool_name is None

    def test_frozen(self) -> None:
        req = MemoryWriteRequest("c", "model_response", 1, 0, None, None)
        with pytest.raises(Exception):
            req.content = "other"  # type: ignore[misc]

