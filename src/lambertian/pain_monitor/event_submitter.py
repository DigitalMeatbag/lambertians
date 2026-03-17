"""Client-side pain event submission — appends to event_queue.jsonl (IS-8.7)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from lambertian.contracts.pain_records import PainEvent

_log = logging.getLogger(__name__)


class FilePainEventSubmitter:
    """Submits PainEvent records to the shared event_queue.jsonl file.

    Implements PainEventSubmitter protocol structurally (no explicit inheritance).
    """

    def __init__(self, queue_path: Path) -> None:
        self._queue_path = queue_path

    def submit(self, event: PainEvent) -> None:
        """Append a single JSON line to event_queue.jsonl with immediate flush."""
        record = {
            "event_id": event.event_id,
            "incident_type": event.incident_type,
            "severity": event.severity,
            "description": event.description,
            "turn_number": event.turn_number,
            "submitted_at": event.submitted_at,
            "context": event.context,
        }
        try:
            self._queue_path.parent.mkdir(parents=True, exist_ok=True)
            with self._queue_path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
                fh.flush()
        except OSError as exc:
            _log.error("Could not submit pain event to queue: %s", exc)
