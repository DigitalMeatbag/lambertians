"""Tests for FitnessCursorStore."""
from __future__ import annotations

from pathlib import Path

from lambertian.fitness.cursor_state import FitnessCursorState, FitnessCursorStore


def test_read_absent_file_returns_zero_state(tmp_path: Path) -> None:
    store = FitnessCursorStore(tmp_path / "nonexistent" / "state.json")
    state = store.read()
    assert state.last_computed_turn == 0
    assert state.cumulative_pain == 0.0
    assert state.pain_history_cursor == 0
    assert state.event_stream_cursor == 0
    assert state.meaningful_event_count == 0
    assert state.last_score == 0.0


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    store = FitnessCursorStore(state_path)

    original = FitnessCursorState(
        last_computed_turn=42,
        cumulative_pain=3.14,
        pain_history_cursor=1024,
        event_stream_cursor=2048,
        meaningful_event_count=17,
        last_score=0.75,
    )
    store.write(original)

    assert state_path.exists()
    recovered = store.read()

    assert recovered.last_computed_turn == 42
    assert recovered.cumulative_pain == 3.14
    assert recovered.pain_history_cursor == 1024
    assert recovered.event_stream_cursor == 2048
    assert recovered.meaningful_event_count == 17
    assert recovered.last_score == 0.75


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    state_path = tmp_path / "nested" / "deep" / "state.json"
    store = FitnessCursorStore(state_path)
    state = FitnessCursorState(
        last_computed_turn=1,
        cumulative_pain=0.0,
        pain_history_cursor=0,
        event_stream_cursor=0,
        meaningful_event_count=0,
        last_score=0.0,
    )
    store.write(state)
    assert state_path.exists()


def test_write_is_atomic(tmp_path: Path) -> None:
    """Verify that no .tmp file is left behind after write."""
    state_path = tmp_path / "state.json"
    store = FitnessCursorStore(state_path)
    state = FitnessCursorState(
        last_computed_turn=5,
        cumulative_pain=1.0,
        pain_history_cursor=100,
        event_stream_cursor=200,
        meaningful_event_count=3,
        last_score=0.5,
    )
    store.write(state)
    tmp = state_path.with_suffix(".tmp")
    assert not tmp.exists()
    assert state_path.exists()
