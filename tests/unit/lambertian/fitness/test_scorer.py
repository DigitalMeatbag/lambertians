"""Tests for FitnessScorer."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lambertian.fitness.cursor_state import FitnessCursorState, FitnessCursorStore
from lambertian.fitness.registry import FitnessFunctionRegistry, build_default_registry
from lambertian.fitness.scorer import FitnessScore, FitnessScorer


def _make_config(
    max_age: int = 1000,
    expected_events: float = 25.0,
    pain_baseline: float = 10.0,
    min_denom: float = 0.10,
    active_fn: str = "phase1_baseline",
) -> object:
    """Build a minimal mock Config object."""
    config = MagicMock()
    config.universe.max_age_turns = max_age
    config.fitness.expected_events_per_100_turns = expected_events
    config.fitness.normalized_pain_baseline = pain_baseline
    config.fitness.minimum_denominator = min_denom
    config.fitness.active_function = active_fn
    return config


def _make_scorer(
    tmp_path: Path,
    *,
    cursor_state: FitnessCursorState | None = None,
    new_events: int = 0,
    new_event_histogram: dict[str, int] | None = None,
    new_event_cursor: int = 0,
    new_pain: float = 0.0,
    new_pain_cursor: int = 0,
    config: object | None = None,
) -> tuple[FitnessScorer, MagicMock, MagicMock, MagicMock]:
    if config is None:
        config = _make_config()

    registry = build_default_registry()
    output_path = tmp_path / "score.json"

    cursor_store = MagicMock(spec=FitnessCursorStore)
    cursor_store.read.return_value = cursor_state or FitnessCursorState(
        last_computed_turn=0,
        cumulative_pain=0.0,
        pain_history_cursor=0,
        event_stream_cursor=0,
        meaningful_event_count=0,
        last_score=0.0,
    )

    # Build histogram from new_events count if not explicitly provided.
    if new_event_histogram is None:
        histogram: dict[str, int] = {"TOOL_CALL": new_events} if new_events > 0 else {}
    else:
        histogram = new_event_histogram

    event_reader = MagicMock()
    event_reader.count_new_events_by_type.return_value = (histogram, new_event_cursor)

    pain_reader = MagicMock()
    pain_reader.sum_new_pain.return_value = (new_pain, new_pain_cursor)

    scorer = FitnessScorer(
        config=config,  # type: ignore[arg-type]
        registry=registry,
        cursor_store=cursor_store,
        event_reader=event_reader,
        pain_reader=pain_reader,
        output_path=output_path,
    )
    return scorer, cursor_store, event_reader, pain_reader


def test_compute_running_reads_cursor(tmp_path: Path) -> None:
    scorer, cursor_store, _, _ = _make_scorer(tmp_path)
    scorer.compute_running(10)
    cursor_store.read.assert_called_once()


def test_compute_running_writes_cursor(tmp_path: Path) -> None:
    scorer, cursor_store, _, _ = _make_scorer(
        tmp_path, new_events=5, new_event_cursor=100, new_pain=2.0, new_pain_cursor=50
    )
    scorer.compute_running(10)
    cursor_store.write.assert_called_once()
    written_state: FitnessCursorState = cursor_store.write.call_args[0][0]
    assert written_state.meaningful_event_count == 5
    assert written_state.cumulative_pain == pytest.approx(2.0)
    assert written_state.last_computed_turn == 10


def test_compute_running_writes_score_file(tmp_path: Path) -> None:
    scorer, _, _, _ = _make_scorer(tmp_path)
    result = scorer.compute_running(50)
    output = tmp_path / "score.json"
    assert output.exists()
    data = json.loads(output.read_text())
    assert data["turn_number"] == 50
    assert data["score"] == pytest.approx(result.score)


def test_compute_running_accumulates_pain_and_events(tmp_path: Path) -> None:
    initial = FitnessCursorState(
        last_computed_turn=5,
        cumulative_pain=1.0,
        pain_history_cursor=50,
        event_stream_cursor=100,
        meaningful_event_count=3,
        last_score=0.1,
    )
    scorer, cursor_store, _, _ = _make_scorer(
        tmp_path,
        cursor_state=initial,
        new_events=2,
        new_pain=0.5,
    )
    scorer.compute_running(10)
    written: FitnessCursorState = cursor_store.write.call_args[0][0]
    assert written.meaningful_event_count == 5  # 3 + 2
    assert written.cumulative_pain == pytest.approx(1.5)  # 1.0 + 0.5


def test_compute_postmortem_creates_fresh_readers(tmp_path: Path) -> None:
    """Post-mortem should compute from scratch, ignoring cursor state."""
    config = _make_config(max_age=100)
    registry = build_default_registry()
    output_path = tmp_path / "score.json"

    # Cursor store has non-zero state — postmortem must ignore it
    cursor_store = MagicMock(spec=FitnessCursorStore)
    event_reader = MagicMock()
    event_reader.count_new_meaningful_events.return_value = (0, 0)
    pain_reader = MagicMock()
    pain_reader.sum_new_pain.return_value = (0.0, 0)

    scorer = FitnessScorer(
        config=config,  # type: ignore[arg-type]
        registry=registry,
        cursor_store=cursor_store,
        event_reader=event_reader,
        pain_reader=pain_reader,
        output_path=output_path,
    )

    event_dir = tmp_path / "event_stream"
    event_dir.mkdir()
    pain_file = tmp_path / "pain_history.jsonl"
    pain_file.write_text("")

    result = scorer.compute_postmortem(
        event_stream_dir=event_dir,
        pain_history_path=pain_file,
        final_turn=50,
    )
    assert isinstance(result, FitnessScore)
    assert result.turn_number == 50
    assert output_path.exists()


def test_compute_running_accumulates_histogram(tmp_path: Path) -> None:
    """Histogram in cursor state merges new counts with existing cumulative counts."""
    initial = FitnessCursorState(
        last_computed_turn=5,
        cumulative_pain=0.0,
        pain_history_cursor=0,
        event_stream_cursor=100,
        meaningful_event_count=3,
        last_score=0.1,
        event_type_histogram={"TOOL_CALL": 2, "MEMORY_WRITE": 1},
    )
    scorer, cursor_store, _, _ = _make_scorer(
        tmp_path,
        cursor_state=initial,
        new_event_histogram={"TOOL_CALL": 1, "REVIEWED_ADAPTATION": 2},
    )
    scorer.compute_running(10)
    written: FitnessCursorState = cursor_store.write.call_args[0][0]
    assert written.event_type_histogram == {
        "TOOL_CALL": 3,
        "MEMORY_WRITE": 1,
        "REVIEWED_ADAPTATION": 2,
    }
    assert written.meaningful_event_count == 6  # 3 + 3 (sum of new_event_histogram)


def test_compute_running_with_quality_function(tmp_path: Path) -> None:
    """Quality-weighted active function uses histogram from cursor state."""
    from lambertian.configuration.universe_config import FitnessQualityConfig
    from lambertian.fitness.registry import build_default_registry

    quality_cfg = FitnessQualityConfig(
        primary_weight=1.0, repetition_weight=0.1, expected_quality_score=500.0
    )
    config = _make_config(active_fn="phase2_quality_weighted")
    registry = build_default_registry(quality_config=quality_cfg)
    output_path = tmp_path / "score.json"

    cursor_store = MagicMock(spec=FitnessCursorStore)
    cursor_store.read.return_value = FitnessCursorState(
        last_computed_turn=0,
        cumulative_pain=0.0,
        pain_history_cursor=0,
        event_stream_cursor=0,
        meaningful_event_count=0,
        last_score=0.0,
        event_type_histogram={},
    )

    event_reader = MagicMock()
    event_reader.count_new_events_by_type.return_value = (
        {"TOOL_CALL": 3, "MEMORY_WRITE": 2},
        100,
    )
    pain_reader = MagicMock()
    pain_reader.sum_new_pain.return_value = (0.0, 0)

    scorer = FitnessScorer(
        config=config,  # type: ignore[arg-type]
        registry=registry,
        cursor_store=cursor_store,
        event_reader=event_reader,
        pain_reader=pain_reader,
        output_path=output_path,
    )
    result = scorer.compute_running(100)
    assert isinstance(result, FitnessScore)
    assert result.score > 0.0
    assert output_path.exists()


def test_compute_postmortem_builds_histogram(tmp_path: Path) -> None:
    """Post-mortem scan builds histogram from event files."""
    import json as _json

    config = _make_config(max_age=100)
    registry = build_default_registry()
    output_path = tmp_path / "score.json"

    cursor_store = MagicMock(spec=FitnessCursorStore)
    event_reader = MagicMock()
    event_reader.count_new_events_by_type.return_value = (0, 0)
    pain_reader = MagicMock()
    pain_reader.sum_new_pain.return_value = (0.0, 0)

    scorer = FitnessScorer(
        config=config,  # type: ignore[arg-type]
        registry=registry,
        cursor_store=cursor_store,
        event_reader=event_reader,
        pain_reader=pain_reader,
        output_path=output_path,
    )

    event_dir = tmp_path / "event_stream"
    event_dir.mkdir()
    events_file = event_dir / "events.jsonl"
    with events_file.open("w") as f:
        f.write(_json.dumps({"event_type": "TOOL_CALL"}) + "\n")
        f.write(_json.dumps({"event_type": "TOOL_CALL"}) + "\n")
        f.write(_json.dumps({"event_type": "MEMORY_WRITE"}) + "\n")
        f.write(_json.dumps({"event_type": "TURN_COMPLETE"}) + "\n")  # not meaningful

    pain_file = tmp_path / "pain_history.jsonl"
    pain_file.write_text("")

    result = scorer.compute_postmortem(
        event_stream_dir=event_dir,
        pain_history_path=pain_file,
        final_turn=50,
    )
    assert isinstance(result, FitnessScore)
    assert result.meaningful_event_count == 3  # 2 TOOL_CALL + 1 MEMORY_WRITE
    assert output_path.exists()

