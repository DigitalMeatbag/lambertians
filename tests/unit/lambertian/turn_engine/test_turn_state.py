"""Unit tests for TurnStateStore. IS-6."""

from __future__ import annotations

from pathlib import Path

import pytest

from lambertian.turn_engine.turn_state import TurnStateStore


@pytest.fixture()
def store(tmp_path: Path) -> TurnStateStore:
    return TurnStateStore(tmp_path)


class TestReadTurnNumber:
    def test_returns_zero_when_absent(self, store: TurnStateStore) -> None:
        assert store.read_turn_number() == 0

    def test_returns_stored_value(self, store: TurnStateStore, tmp_path: Path) -> None:
        (tmp_path / "turn_state.json").write_text('{"turn_number": 7}', encoding="utf-8")
        assert store.read_turn_number() == 7


class TestIncrementTurn:
    def test_first_increment_returns_one(self, store: TurnStateStore) -> None:
        assert store.increment_turn() == 1

    def test_second_increment_returns_two(self, store: TurnStateStore) -> None:
        store.increment_turn()
        assert store.increment_turn() == 2

    def test_persisted_across_instances(self, tmp_path: Path) -> None:
        store1 = TurnStateStore(tmp_path)
        store1.increment_turn()
        store1.increment_turn()
        store2 = TurnStateStore(tmp_path)
        assert store2.read_turn_number() == 2


class TestWorkingMemory:
    def test_returns_none_when_absent(self, store: TurnStateStore) -> None:
        assert store.read_working_memory() is None

    def test_write_then_read_roundtrip(self, store: TurnStateStore) -> None:
        store.write_working_memory("hello world", turn_number=3)
        assert store.read_working_memory() == "hello world"

    def test_overwrite_updates_content(self, store: TurnStateStore) -> None:
        store.write_working_memory("first", turn_number=1)
        store.write_working_memory("second", turn_number=2)
        assert store.read_working_memory() == "second"


class TestNoopState:
    def test_returns_zero_when_absent(self, store: TurnStateStore) -> None:
        assert store.read_noop_state() == 0

    def test_write_then_read_roundtrip(self, store: TurnStateStore) -> None:
        store.write_noop_state(5)
        assert store.read_noop_state() == 5

    def test_write_zero_resets(self, store: TurnStateStore) -> None:
        store.write_noop_state(3)
        store.write_noop_state(0)
        assert store.read_noop_state() == 0


class TestRecentSelfPrompts:
    def test_returns_empty_when_absent(self, store: TurnStateStore) -> None:
        assert store.read_recent_self_prompts(10) == []

    def test_append_then_read(self, store: TurnStateStore) -> None:
        store.append_self_prompt("What is this?", turn_number=1, max_entries=10)
        result = store.read_recent_self_prompts(10)
        assert len(result) == 1
        assert result[0]["text"] == "What is this?"
        assert result[0]["turn"] == 1

    def test_ring_buffer_trimming(self, store: TurnStateStore) -> None:
        for i in range(5):
            store.append_self_prompt(f"prompt {i}", turn_number=i, max_entries=3)
        result = store.read_recent_self_prompts(3)
        assert len(result) == 3
        # Should have the last 3 entries
        assert result[0]["text"] == "prompt 2"
        assert result[1]["text"] == "prompt 3"
        assert result[2]["text"] == "prompt 4"

    def test_max_entries_respected_on_read(self, store: TurnStateStore) -> None:
        for i in range(5):
            store.append_self_prompt(f"prompt {i}", turn_number=i, max_entries=10)
        result = store.read_recent_self_prompts(2)
        assert len(result) == 2

