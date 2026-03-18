"""Byte-offset cursor reader for the event_queue.jsonl append-only file (IS-8.3.3)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from lambertian.contracts.pain_records import PainEvent

_log = logging.getLogger(__name__)


class EventQueueReader:
    """Reads new events from event_queue.jsonl since the last cursor position."""

    def __init__(self, queue_path: Path, cursor_path: Path) -> None:
        self._queue_path = queue_path
        self._cursor_path = cursor_path

    def current_offset(self) -> int:
        """Return current cursor byte offset; 0 if cursor file is absent."""
        if not self._cursor_path.exists():
            return 0
        try:
            raw = json.loads(self._cursor_path.read_text())
            return int(raw["offset"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            _log.warning("Could not read event queue cursor: %s", exc)
            return 0

    def read_new_events(self) -> list[PainEvent]:
        """Read events from the current cursor offset; returns empty list if no new data."""
        if not self._queue_path.exists():
            return []

        offset = self.current_offset()
        events: list[PainEvent] = []

        try:
            with self._queue_path.open("rb") as fh:
                fh.seek(offset)
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        event = PainEvent(
                            event_id=str(obj["event_id"]),
                            incident_type=str(obj["incident_type"]),
                            severity=float(obj["severity"]),
                            description=str(obj["description"]),
                            turn_number=int(obj["turn_number"]),
                            submitted_at=str(obj["submitted_at"]),
                            context=(
                                {str(k): str(v) for k, v in obj["context"].items()}
                                if obj.get("context") is not None
                                else None
                            ),
                        )
                        events.append(event)
                    except (KeyError, ValueError, json.JSONDecodeError) as exc:
                        _log.warning("Skipping malformed event queue line: %s", exc)
        except OSError as exc:
            _log.warning("Could not read event queue: %s", exc)

        return events

    def advance_cursor(self, new_offset: int) -> None:
        """Persist the new cursor offset."""
        data = json.dumps({"offset": new_offset})
        tmp = self._cursor_path.with_suffix(".tmp")
        try:
            tmp.write_text(data)
            os.replace(tmp, self._cursor_path)  # atomic on both POSIX and Windows
        except OSError as exc:
            _log.warning("Could not advance event queue cursor: %s", exc)

    def queue_file_size(self) -> int:
        """Return the current byte size of the queue file (used to advance cursor after read)."""
        try:
            return self._queue_path.stat().st_size
        except OSError:
            return self.current_offset()
