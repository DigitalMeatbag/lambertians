"""Append-only event stream writer. IS-9."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import IO

from lambertian.configuration.universe_config import Config

_log = logging.getLogger(__name__)


class EventLogWriteError(Exception):
    """Fatal I/O error writing to the event log."""


class EventLogWriter:
    """Append-only event stream writer. IS-9."""

    def __init__(self, config: Config) -> None:
        self._config = config
        active_path = os.path.abspath(config.paths.event_stream_file)
        self._active_path: str = active_path
        self._base_dir: str = os.path.dirname(active_path)
        os.makedirs(self._base_dir, exist_ok=True)
        self._file: IO[str] = open(self._active_path, "a", encoding="utf-8")
        self._current_size: int = (
            os.path.getsize(self._active_path)
            if os.path.exists(self._active_path)
            else 0
        )
        self._last_flush_time: float = time.monotonic()

    def write_event(
        self,
        event_type: str,
        turn_number: int,
        source_service: str,
        extra: dict[str, object],  # object: heterogeneous per-event fields
    ) -> None:
        """Write one event record. Fatal on I/O error."""
        now = datetime.now(timezone.utc)
        timestamp = (
            now.strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{now.microsecond // 1000:03d}Z"
        )
        record: dict[str, object] = {
            "event_type": event_type,
            "event_id": str(uuid.uuid4()),
            "instance_id": self._config.universe.instance_id,
            "timestamp": timestamp,
            "turn_number": turn_number,
            "source_service": source_service,
            **extra,
        }
        line = json.dumps(record) + "\n"
        try:
            self._file.write(line)
        except OSError as exc:
            msg = f"EventLogWriter: write failed: {exc}"
            sys.stderr.write(msg + "\n")
            raise EventLogWriteError(msg) from exc

        self._current_size += len(line.encode("utf-8"))

        is_critical = event_type in ("DEATH_TRIGGER", "TURN_FAILED")
        now_mono = time.monotonic()
        elapsed = now_mono - self._last_flush_time
        if is_critical or elapsed >= self._config.event_stream.flush_interval_seconds:
            try:
                self._file.flush()
            except OSError as exc:
                msg = f"EventLogWriter: flush failed: {exc}"
                sys.stderr.write(msg + "\n")
                raise EventLogWriteError(msg) from exc
            self._last_flush_time = now_mono

        max_bytes = self._config.event_stream.max_file_size_mb * 1024 * 1024
        if self._current_size >= max_bytes:
            self._rotate()

    def _rotate(self) -> None:
        """Rotate active events.jsonl to events.<timestamp>.jsonl."""
        try:
            self._file.flush()
            self._file.close()
        except OSError as exc:
            _log.warning("EventLogWriter: error closing file before rotation: %s", exc)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rotated_path = os.path.join(self._base_dir, f"events.{timestamp}.jsonl")
        os.replace(self._active_path, rotated_path)

        self._file = open(self._active_path, "a", encoding="utf-8")
        self._current_size = 0
        self._last_flush_time = time.monotonic()

        self._prune_archives()

    def _prune_archives(self) -> None:
        """Delete oldest rotated archives if count exceeds max_archives."""
        archives = sorted(
            entry.path
            for entry in os.scandir(self._base_dir)
            if (
                entry.is_file()
                and entry.name.startswith("events.")
                and entry.name.endswith(".jsonl")
                and entry.name != "events.jsonl"
            )
        )
        max_archives = self._config.event_stream.max_archives
        while len(archives) > max_archives:
            oldest = archives.pop(0)
            try:
                os.remove(oldest)
            except OSError as exc:
                _log.warning(
                    "EventLogWriter: failed to delete archive %s: %s", oldest, exc
                )

    def close(self) -> None:
        """Flush and close the event log file."""
        try:
            self._file.flush()
            self._file.close()
        except OSError as exc:
            _log.warning("EventLogWriter: close error: %s", exc)
