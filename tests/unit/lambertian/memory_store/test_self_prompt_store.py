"""Tests for SelfPromptStore. IS-10.3."""
from __future__ import annotations
from pathlib import Path
import pytest
from lambertian.memory_store.self_prompt_store import SelfPromptStore


def _unit_embedding(text: str) -> list[float]:
    """Fake embedding: constant unit vector [1.0, 0.0]."""
    return [1.0, 0.0]


def _zero_embedding(text: str) -> list[float]:
    return [0.0, 1.0]


@pytest.fixture()
def store(tmp_path: Path) -> SelfPromptStore:
    return SelfPromptStore(
        store_path=tmp_path / "self_prompts.json",
        capacity=3,
        embedding_fn=_unit_embedding,
    )


class TestGetRecent:
    def test_returns_empty_when_absent(self, store: SelfPromptStore) -> None:
        assert store.get_recent() == []


class TestAppend:
    def test_append_and_read_back(self, store: SelfPromptStore) -> None:
        store.append("What is going on?", turn_number=1)
        entries = store.get_recent()
        assert len(entries) == 1
        assert entries[0]["content"] == "What is going on?"
        assert entries[0]["turn_number"] == 1
        assert "embedding" in entries[0]

    def test_ring_buffer_capacity_enforced(self, store: SelfPromptStore) -> None:
        for i in range(5):
            store.append(f"prompt {i}", turn_number=i)
        entries = store.get_recent()
        assert len(entries) == 3
        assert entries[0]["content"] == "prompt 2"
        assert entries[2]["content"] == "prompt 4"


class TestComputeMaxSimilarity:
    def test_returns_zero_when_empty(self, store: SelfPromptStore) -> None:
        assert store.compute_max_similarity("anything") == 0.0

    def test_identical_embedding_gives_high_similarity(
        self, store: SelfPromptStore
    ) -> None:
        # Both stored and candidate use _unit_embedding → [1.0, 0.0]
        store.append("stored text", turn_number=1)
        sim = store.compute_max_similarity("candidate text")
        assert sim == pytest.approx(1.0)

    def test_orthogonal_embeddings_give_zero_similarity(
        self, tmp_path: Path
    ) -> None:
        # Store uses unit [1,0], candidate uses [0,1]
        s = SelfPromptStore(tmp_path / "sp.json", 3, _unit_embedding)
        s.append("stored", turn_number=1)
        # Manually compute with different embedding
        s2 = SelfPromptStore(tmp_path / "sp.json", 3, _zero_embedding)
        sim = s2.compute_max_similarity("candidate")
        assert sim == pytest.approx(0.0)

