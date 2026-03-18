"""Tests for EventStreamReader."""
from __future__ import annotations

import json
from pathlib import Path

from lambertian.fitness.event_reader import EventStreamReader


def _write_events(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_count_meaningful_events_from_offset_zero(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    _write_events(
        event_file,
        [
            {"event_type": "TOOL_CALL", "turn_number": 1},
            {"event_type": "TURN_COMPLETE", "turn_number": 1},
            {"event_type": "MEMORY_WRITE", "turn_number": 1},
            {"event_type": "TURN_START", "turn_number": 2},
            {"event_type": "REVIEWED_ADAPTATION", "turn_number": 2},
            {"event_type": "ADAPTATION_FORBIDDEN", "turn_number": 3},
        ],
    )
    reader = EventStreamReader(tmp_path)
    count, offset = reader.count_new_meaningful_events(0)
    assert count == 4  # TOOL_CALL, MEMORY_WRITE, REVIEWED_ADAPTATION, ADAPTATION_FORBIDDEN
    assert offset == event_file.stat().st_size


def test_cursor_advances_to_end(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    _write_events(event_file, [{"event_type": "TOOL_CALL"}])
    reader = EventStreamReader(tmp_path)
    _, offset = reader.count_new_meaningful_events(0)
    assert offset == event_file.stat().st_size


def test_absent_file_returns_zero(tmp_path: Path) -> None:
    reader = EventStreamReader(tmp_path)  # events.jsonl doesn't exist
    count, offset = reader.count_new_meaningful_events(0)
    assert count == 0
    assert offset == 0


def test_count_from_mid_file_offset(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    lines: list[dict[str, object]] = [
        {"event_type": "TOOL_CALL"},
        {"event_type": "MEMORY_WRITE"},
    ]
    _write_events(event_file, lines)

    # Get offset after first line
    reader = EventStreamReader(tmp_path)
    count_first, first_offset = reader.count_new_meaningful_events(0)
    assert count_first == 2

    # Seek to after first line — only the second should count
    first_line_bytes = len((json.dumps(lines[0]) + "\n").encode("utf-8"))
    count_second, second_offset = reader.count_new_meaningful_events(first_line_bytes)
    assert count_second == 1
    assert second_offset == event_file.stat().st_size


def test_skips_unparseable_lines(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    event_file.parent.mkdir(parents=True, exist_ok=True)
    with open(event_file, "w", encoding="utf-8") as f:
        f.write('{"event_type": "TOOL_CALL"}\n')
        f.write("not valid json\n")
        f.write('{"event_type": "MEMORY_WRITE"}\n')

    reader = EventStreamReader(tmp_path)
    count, _ = reader.count_new_meaningful_events(0)
    assert count == 2


# ---------------------------------------------------------------------------
# count_new_events_by_type — Phase 2 histogram method
# ---------------------------------------------------------------------------

def test_count_by_type_returns_histogram(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    _write_events(
        event_file,
        [
            {"event_type": "TOOL_CALL", "turn_number": 1},
            {"event_type": "TOOL_CALL", "turn_number": 2},
            {"event_type": "MEMORY_WRITE", "turn_number": 2},
            {"event_type": "TURN_COMPLETE", "turn_number": 2},  # not meaningful
            {"event_type": "REVIEWED_ADAPTATION", "turn_number": 3},
        ],
    )
    reader = EventStreamReader(tmp_path)
    histogram, offset = reader.count_new_events_by_type(0)
    assert histogram == {"TOOL_CALL": 2, "MEMORY_WRITE": 1, "REVIEWED_ADAPTATION": 1}
    assert offset == event_file.stat().st_size


def test_count_by_type_absent_file_returns_empty(tmp_path: Path) -> None:
    reader = EventStreamReader(tmp_path)
    histogram, offset = reader.count_new_events_by_type(0)
    assert histogram == {}
    assert offset == 0


def test_count_by_type_mid_file_offset(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    lines: list[dict[str, object]] = [
        {"event_type": "TOOL_CALL"},
        {"event_type": "MEMORY_WRITE"},
    ]
    _write_events(event_file, lines)

    import json as _json
    first_line_bytes = len((_json.dumps(lines[0]) + "\n").encode("utf-8"))
    reader = EventStreamReader(tmp_path)
    histogram, _ = reader.count_new_events_by_type(first_line_bytes)
    assert histogram == {"MEMORY_WRITE": 1}
    assert "TOOL_CALL" not in histogram


def test_count_new_meaningful_events_delegates_to_histogram(tmp_path: Path) -> None:
    event_file = tmp_path / "events.jsonl"
    _write_events(
        event_file,
        [
            {"event_type": "TOOL_CALL"},
            {"event_type": "TOOL_CALL"},
            {"event_type": "MEMORY_WRITE"},
        ],
    )
    reader = EventStreamReader(tmp_path)
    count, _ = reader.count_new_meaningful_events(0)
    assert count == 3  # sum of histogram values

