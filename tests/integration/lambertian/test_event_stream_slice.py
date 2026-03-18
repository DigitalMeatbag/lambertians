"""Integration tests — event stream writer → rotation → fitness event reader."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from lambertian.configuration.universe_config import Config
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.event_reader import EventStreamReader, MEANINGFUL_EVENT_TYPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tiny_rotation_config(config: Config) -> Config:
    """Return config with max_file_size_mb=0 so rotation fires after every write."""
    new_event_stream = dataclasses.replace(
        config.event_stream,
        max_file_size_mb=0,
        max_archives=10,
    )
    return dataclasses.replace(config, event_stream=new_event_stream)


def _write_typed_event(writer: EventLogWriter, event_type: str, turn: int = 0) -> None:
    writer.write_event(event_type, turn, "test", {})


def _collect_all_events(event_dir: Path) -> list[dict[str, object]]:
    """Collect every event record from all *.jsonl files in event_dir."""
    records: list[dict[str, object]] = []
    for f in sorted(event_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    records.append(obj)
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEventStreamRotation:
    def test_rotation_creates_archive_file(
        self, config: Config, tmp_path: Path
    ) -> None:
        """Writing enough events to exceed max_file_size_mb triggers rotation
        and produces at least one archive file named events.<timestamp>.jsonl."""
        small_config = _tiny_rotation_config(config)
        event_dir = Path(small_config.paths.event_stream_file).parent
        event_dir.mkdir(parents=True, exist_ok=True)

        writer = EventLogWriter(small_config)
        # Three writes; with max_file_size_mb=0 each write triggers rotation.
        _write_typed_event(writer, "STARTUP", turn=0)
        _write_typed_event(writer, "TURN_START", turn=1)
        _write_typed_event(writer, "TURN_COMPLETE", turn=1)
        writer.close()

        archives = [
            p
            for p in event_dir.iterdir()
            if p.name.startswith("events.") and p.name != "events.jsonl"
        ]
        assert archives, "at least one archive file must exist after rotation"
        # Archive names must match events.<timestamp>.jsonl pattern.
        for arch in archives:
            assert arch.suffix == ".jsonl"
            # e.g. "events.20250101T120000000000Z.jsonl"
            name_without_ext = arch.name[: -len(".jsonl")]
            assert name_without_ext.startswith("events.")

    def test_rotation_preserves_all_written_events(
        self, config: Config, tmp_path: Path
    ) -> None:
        """Combined content of all archives + current file contains every event written."""
        small_config = _tiny_rotation_config(config)
        event_dir = Path(small_config.paths.event_stream_file).parent
        event_dir.mkdir(parents=True, exist_ok=True)

        writer = EventLogWriter(small_config)
        written_types = ["STARTUP", "TURN_START", "TURN_COMPLETE"]
        for et in written_types:
            _write_typed_event(writer, et)
        writer.close()

        all_events = _collect_all_events(event_dir)
        found_types = [e.get("event_type") for e in all_events]
        for et in written_types:
            assert et in found_types, f"{et} must appear in combined event data"


class TestEventStreamReaderMeaningfulCounts:
    def test_counts_only_meaningful_event_types(
        self, config: Config, tmp_path: Path
    ) -> None:
        """EventStreamReader.count_new_meaningful_events counts only MEANINGFUL_EVENT_TYPES.

        Write: TURN_COMPLETE×3, TOOL_CALL×2, STARTUP×1, MEMORY_WRITE×1
        Expected meaningful count: TOOL_CALL(2) + MEMORY_WRITE(1) = 3
        """
        event_dir = Path(config.paths.event_stream_file).parent
        event_dir.mkdir(parents=True, exist_ok=True)

        events_file = event_dir / "events.jsonl"
        rows: list[dict[str, object]] = []
        for _ in range(3):
            rows.append({"event_type": "TURN_COMPLETE"})
        for _ in range(2):
            rows.append({"event_type": "TOOL_CALL"})
        rows.append({"event_type": "STARTUP"})
        rows.append({"event_type": "MEMORY_WRITE"})

        events_file.write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n",
            encoding="utf-8",
        )

        reader = EventStreamReader(event_dir)
        count, _cursor = reader.count_new_meaningful_events(0)
        assert count == 3, f"expected 3 meaningful events, got {count}"

    def test_meaningful_event_types_constant_matches_spec(self) -> None:
        """Sanity check: MEANINGFUL_EVENT_TYPES includes the expected keys."""
        assert "TOOL_CALL" in MEANINGFUL_EVENT_TYPES
        assert "MEMORY_WRITE" in MEANINGFUL_EVENT_TYPES
        assert "TURN_COMPLETE" not in MEANINGFUL_EVENT_TYPES
        assert "STARTUP" not in MEANINGFUL_EVENT_TYPES

    def test_byte_offset_resumes_correctly(
        self, config: Config, tmp_path: Path
    ) -> None:
        """Passing a non-zero byte offset skips already-counted events."""
        event_dir = Path(config.paths.event_stream_file).parent
        event_dir.mkdir(parents=True, exist_ok=True)

        events_file = event_dir / "events.jsonl"
        first_line = json.dumps({"event_type": "TOOL_CALL"}) + "\n"
        second_line = json.dumps({"event_type": "MEMORY_WRITE"}) + "\n"
        events_file.write_text(first_line + second_line, encoding="utf-8")

        reader = EventStreamReader(event_dir)

        # From offset 0 we see both.
        count_full, offset_after_first = reader.count_new_meaningful_events(0)
        assert count_full == 2

        # From the offset returned by the first scan the reader finds nothing new
        # (all lines already past).
        count_incremental, _ = reader.count_new_meaningful_events(offset_after_first)
        assert count_incremental == 0
