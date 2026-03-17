"""Delivery queue — pain_monitor appends; turn_engine drains (IS-8.4.4)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from lambertian.contracts.pain_records import PainMessage

_log = logging.getLogger(__name__)


class DeliveryQueue:
    """Shared delivery queue persisted as a JSON array file.

    Pain-monitor appends messages; turn_engine drains atomically.
    Implements PainDeliveryDrain protocol structurally.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def append_message(self, message: PainMessage) -> None:
        """Append one PainMessage to the delivery queue (atomic read-modify-write)."""
        current = self._read_array()
        current.append(self._to_dict(message))
        self._atomic_write(self._path, json.dumps(current))

    def drain(self) -> list[PainMessage]:
        """Read all messages and atomically replace the queue with an empty array."""
        current = self._read_array()
        self._atomic_write(self._path, "[]")
        messages: list[PainMessage] = []
        for item in current:
            try:
                messages.append(
                    PainMessage(
                        channel=str(item["channel"]),
                        severity=float(item["severity"]),
                        urgency=str(item["urgency"]),
                        description=str(item["description"]),
                        context=str(item["context"]) if item.get("context") is not None else None,
                    )
                )
            except (KeyError, ValueError) as exc:
                _log.warning("Skipping malformed delivery queue entry: %s", exc)
        return messages

    def _read_array(self) -> list[Any]:
        if not self._path.exists():
            return []
        try:
            # Any is required here — the JSON array contents are untyped at read boundary;
            # typed projection is performed in drain() immediately after.
            data: list[Any] = json.loads(self._path.read_text())
            if not isinstance(data, list):
                return []
            return data
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("Could not read delivery queue: %s", exc)
            return []

    def _atomic_write(self, path: Path, data: str) -> None:
        tmp = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(data)
            os.replace(tmp, path)  # atomic on both POSIX and Windows
        except OSError as exc:
            _log.error("Could not write delivery queue: %s", exc)

    def _to_dict(self, message: PainMessage) -> dict[str, object]:
        return {
            "channel": message.channel,
            "severity": message.severity,
            "urgency": message.urgency,
            "description": message.description,
            "context": message.context,
        }
