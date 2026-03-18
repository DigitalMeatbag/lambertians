"""IS-13.4 Event stream reader — counts meaningful events from a byte offset."""
from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

MEANINGFUL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "TOOL_CALL",
        "MEMORY_WRITE",
        "REVIEWED_ADAPTATION",
        "ADAPTATION_FORBIDDEN",
    }
)


class EventStreamReader:
    """IS-13.4. Reads events.jsonl from byte offset, counts meaningful event types."""

    def __init__(self, event_stream_dir: Path) -> None:
        self._event_stream_dir = event_stream_dir

    def count_new_events_by_type(self, from_byte_offset: int) -> tuple[dict[str, int], int]:
        """Return (event_type_histogram, new_byte_offset) for events after from_byte_offset.

        Only counts event types in MEANINGFUL_EVENT_TYPES. If file absent: returns ({}, 0).
        Skips unparseable lines.
        """
        events_file = self._event_stream_dir / "events.jsonl"
        try:
            with open(events_file, "rb") as f:
                f.seek(from_byte_offset)
                histogram: dict[str, int] = {}
                for raw_line in f:
                    try:
                        record: object = json.loads(raw_line)
                        if not isinstance(record, dict):
                            continue
                        event_type = record.get("event_type")
                        if isinstance(event_type, str) and event_type in MEANINGFUL_EVENT_TYPES:
                            histogram[event_type] = histogram.get(event_type, 0) + 1
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        _log.warning(
                            "EventStreamReader: skipping unparseable line at offset %d",
                            from_byte_offset,
                        )
                return histogram, f.tell()
        except FileNotFoundError:
            return {}, 0

    def count_new_meaningful_events(self, from_byte_offset: int) -> tuple[int, int]:
        """Return (count, new_byte_offset). If file absent: returns (0, 0).

        Seeks to from_byte_offset. Skips unparseable lines.
        """
        histogram, new_offset = self.count_new_events_by_type(from_byte_offset)
        return sum(histogram.values()), new_offset
