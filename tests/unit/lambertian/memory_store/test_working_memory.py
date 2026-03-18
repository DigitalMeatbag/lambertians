"""Tests for WorkingMemoryStore. IS-10.2."""
from __future__ import annotations
from pathlib import Path
import json
import pytest
from lambertian.memory_store.working_memory import WorkingMemoryStore


@pytest.fixture()
def store(tmp_path: Path) -> WorkingMemoryStore:
    return WorkingMemoryStore(tmp_path, max_chars=100)


class TestRead:
    def test_returns_none_when_absent(self, store: WorkingMemoryStore) -> None:
        assert store.read() is None

    def test_returns_none_on_corrupted_file(self, tmp_path: Path) -> None:
        (tmp_path / "working.json").write_text("not json", encoding="utf-8")
        s = WorkingMemoryStore(tmp_path, max_chars=100)
        assert s.read() is None


class TestWrite:
    def test_write_and_read_roundtrip(self, store: WorkingMemoryStore) -> None:
        store.write("hello world", turn_number=3)
        assert store.read() == "hello world"

    def test_overwrite_updates_content(self, store: WorkingMemoryStore) -> None:
        store.write("first", turn_number=1)
        store.write("second", turn_number=2)
        assert store.read() == "second"

    def test_truncation_at_max_chars(self, store: WorkingMemoryStore) -> None:
        long_content = "A" * 200
        store.write(long_content, turn_number=1)
        result = store.read()
        assert result is not None
        assert len(result) == 100
        assert result == "A" * 100

    def test_schema_compatible_with_turn_state_store(self, tmp_path: Path) -> None:
        """WorkingMemoryStore writes the 'content' key TurnStateStore reads."""
        s = WorkingMemoryStore(tmp_path, max_chars=100)
        s.write("test content", turn_number=5)
        raw = json.loads((tmp_path / "working.json").read_text(encoding="utf-8"))
        assert raw["content"] == "test content"
        assert raw["updated_turn"] == 5
        assert "updated_at" in raw

    def test_atomic_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        s = WorkingMemoryStore(nested, max_chars=50)
        s.write("content", turn_number=1)
        assert s.read() == "content"
