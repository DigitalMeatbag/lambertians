"""Unit tests for EventQueueReader — JSONL read, cursor advance, re-read is empty."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lambertian.pain_monitor.event_queue_reader import EventQueueReader


def _write_event(path: Path, event_id: str, severity: float, turn: int) -> None:
    record = {
        "event_id": event_id,
        "incident_type": "tool_failure",
        "severity": severity,
        "description": f"Event {event_id}",
        "turn_number": turn,
        "submitted_at": "2024-01-01T00:00:00+00:00",
        "context": None,
    }
    with path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def test_read_from_empty_file(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    reader = EventQueueReader(queue, cursor)
    assert reader.read_new_events() == []


def test_read_events_from_file(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    _write_event(queue, "e1", 0.5, 1)
    _write_event(queue, "e2", 0.7, 2)

    reader = EventQueueReader(queue, cursor)
    events = reader.read_new_events()
    assert len(events) == 2
    assert events[0].event_id == "e1"
    assert events[1].event_id == "e2"


def test_advance_cursor_then_reread_is_empty(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    _write_event(queue, "e1", 0.5, 1)

    reader = EventQueueReader(queue, cursor)
    events = reader.read_new_events()
    assert len(events) == 1

    # Advance cursor to end of file.
    new_offset = reader.queue_file_size()
    reader.advance_cursor(new_offset)

    # Now re-reading should return empty.
    events2 = reader.read_new_events()
    assert events2 == []


def test_cursor_persisted(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    _write_event(queue, "e1", 0.5, 1)

    reader = EventQueueReader(queue, cursor)
    file_size = reader.queue_file_size()
    reader.advance_cursor(file_size)

    # Reconstruct reader — cursor should be persisted.
    reader2 = EventQueueReader(queue, cursor)
    assert reader2.current_offset() == file_size


def test_new_events_after_cursor_advance(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    _write_event(queue, "e1", 0.5, 1)

    reader = EventQueueReader(queue, cursor)
    reader.advance_cursor(reader.queue_file_size())

    # Append a new event after advancing the cursor.
    _write_event(queue, "e2", 0.8, 2)
    events = reader.read_new_events()
    assert len(events) == 1
    assert events[0].event_id == "e2"


def test_malformed_line_skipped(tmp_path: Path) -> None:
    queue = tmp_path / "event_queue.jsonl"
    cursor = tmp_path / "cursor.json"
    with queue.open("a") as fh:
        fh.write("{not valid json}\n")
    _write_event(queue, "e1", 0.5, 1)

    reader = EventQueueReader(queue, cursor)
    events = reader.read_new_events()
    # Only the valid event should be returned.
    assert len(events) == 1
    assert events[0].event_id == "e1"

