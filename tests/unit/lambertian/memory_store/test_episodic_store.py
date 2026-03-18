"""Tests for EpisodicStore. IS-10.4."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest

from lambertian.memory_store.retrieval_result import MemoryWriteRequest
from lambertian.memory_store.episodic_store import EpisodicStore, _cosine_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> MagicMock:
    config = MagicMock()
    config.memory.embedding_model = "nomic-embed-text"
    config.memory.minimum_retrieval_score = 0.25
    return config


def _make_store(mock_chroma: MagicMock, mock_httpx: MagicMock) -> EpisodicStore:
    """Build EpisodicStore with mocked chromadb and httpx."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_chroma.HttpClient.return_value = mock_client
    mock_client.get_or_create_collection.return_value = mock_collection
    # Fake embedding response
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_httpx.post.return_value = mock_response
    store = EpisodicStore(_make_config(), "http://ollama:11434")
    return store


# ---------------------------------------------------------------------------
# Tests: _cosine_similarity helper
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# Tests: EpisodicStore.write
# ---------------------------------------------------------------------------


class TestWrite:
    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_returns_correct_document_id(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock, tmp_path: Path
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        request = MemoryWriteRequest(
            content="x" * 100,
            document_type="model_response",
            turn_number=7,
            write_index=2,
            tool_name=None,
            adaptation_class=None,
        )
        doc_id = store.write(request, "inst-001", tmp_path / "stress_state.json")
        assert doc_id == "inst-001-t7-2"

    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_pain_score_defaults_to_zero_when_file_absent(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock, tmp_path: Path
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        request = MemoryWriteRequest(
            content="x" * 100,
            document_type="model_response",
            turn_number=1,
            write_index=0,
            tool_name=None,
            adaptation_class=None,
        )
        store.write(request, "inst-001", tmp_path / "nonexistent.json")
        call_kwargs = mock_collection.add.call_args[1]
        assert call_kwargs["metadatas"][0]["pain_score_at_write"] == 0.0

    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_reads_pain_score_from_file(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock, tmp_path: Path
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        stress_path = tmp_path / "stress_state.json"
        stress_path.write_text(json.dumps({"scalar": 0.42}), encoding="utf-8")
        request = MemoryWriteRequest(
            content="x" * 100,
            document_type="model_response",
            turn_number=1,
            write_index=0,
            tool_name=None,
            adaptation_class=None,
        )
        store.write(request, "inst-001", stress_path)
        call_kwargs = mock_collection.add.call_args[1]
        assert call_kwargs["metadatas"][0]["pain_score_at_write"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# Tests: EpisodicStore.query
# ---------------------------------------------------------------------------


class TestQuery:
    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_filters_below_min_score(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        # distance=1.6 → similarity=1-(1.6/2)=0.2, below min_score=0.25 → filtered out
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[1.6]],
            "documents": [["some content"]],
            "metadatas": [[{"turn_number": 1}]],
        }
        result = store.query("test query", top_k=5, min_score=0.25)
        assert result.retrieval_miss is True
        assert result.documents == []

    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_includes_above_min_score(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        # distance=0.4 → similarity=1-(0.4/2)=0.8, above min_score=0.25 → included
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[0.4]],
            "documents": [["good content"]],
            "metadatas": [[{"turn_number": 1}]],
        }
        result = store.query("test query", top_k=5, min_score=0.25)
        assert result.retrieval_miss is False
        assert len(result.documents) == 1
        assert result.documents[0].content == "good content"
        assert result.documents[0].similarity_score == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Tests: EpisodicStore.check_last_written_similarity
# ---------------------------------------------------------------------------


class TestCheckLastWrittenSimilarity:
    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_empty_collection_returns_zero(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        mock_collection.peek.return_value = {
            "embeddings": None,
            "ids": [],
            "documents": [],
        }
        sim = store.check_last_written_similarity("some content")
        assert sim == 0.0

    @patch("lambertian.memory_store.episodic_store.httpx")
    @patch("lambertian.memory_store.episodic_store.chromadb")
    def test_identical_embedding_gives_one(
        self, mock_chroma: MagicMock, mock_httpx: MagicMock
    ) -> None:
        store = _make_store(mock_chroma, mock_httpx)
        mock_collection = (
            mock_chroma.HttpClient.return_value.get_or_create_collection.return_value
        )
        # Stored embedding matches what httpx will return [0.1, 0.2, 0.3]
        mock_collection.peek.return_value = {
            "embeddings": [[0.1, 0.2, 0.3]],
            "ids": ["doc1"],
        }
        sim = store.check_last_written_similarity("some content")
        assert sim == pytest.approx(1.0)
