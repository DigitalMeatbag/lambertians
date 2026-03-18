"""Runtime state file read/write — IS-6 persistent turn state."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional


class TurnStateStore:
    """Reads/writes runtime/memory/ state files for the turn engine."""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir

    def read_turn_number(self) -> int:
        """Returns current turn number. Returns 0 if file absent (first turn)."""
        path = self._memory_dir / "turn_state.json"
        if not path.exists():
            return 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return int(raw["turn_number"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return 0

    def increment_turn(self) -> int:
        """Increments turn counter atomically. Returns new turn number."""
        current = self.read_turn_number()
        new_turn = current + 1
        self._atomic_write(
            self._memory_dir / "turn_state.json",
            json.dumps({"turn_number": new_turn}),
        )
        return new_turn

    def read_working_memory(self) -> Optional[str]:
        """Returns content string from working.json, or None if absent."""
        path = self._memory_dir / "working.json"
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return str(raw["content"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None

    def write_working_memory(self, content: str, turn_number: int) -> None:
        """Atomically writes working.json."""
        self._atomic_write(
            self._memory_dir / "working.json",
            json.dumps({"content": content, "updated_turn": turn_number}),
        )

    def read_noop_state(self) -> int:
        """Returns consecutive_noop_count. Returns 0 if file absent."""
        path = self._memory_dir / "noop_state.json"
        if not path.exists():
            return 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return int(raw["consecutive_noop_count"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return 0

    def write_noop_state(self, count: int) -> None:
        """Atomically writes noop_state.json."""
        self._atomic_write(
            self._memory_dir / "noop_state.json",
            json.dumps({"consecutive_noop_count": count}),
        )

    def read_recent_self_prompts(self, max_entries: int) -> list[dict[str, object]]:
        """Returns list of {"text": ..., "turn": N} dicts, most recent last."""
        path = self._memory_dir / "recent_self_prompts.json"
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries: list[dict[str, object]] = []
            for item in raw.get("prompts", []):
                entries.append({"text": str(item["text"]), "turn": int(item["turn"])})
            return entries[-max_entries:]
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return []

    def append_self_prompt(
        self, text: str, turn_number: int, max_entries: int
    ) -> None:
        """Appends to ring buffer, trims to max_entries, writes atomically."""
        existing = self.read_recent_self_prompts(max_entries)
        existing.append({"text": text, "turn": turn_number})
        trimmed = existing[-max_entries:]
        self._atomic_write(
            self._memory_dir / "recent_self_prompts.json",
            json.dumps({"prompts": trimmed}),
        )

    def _atomic_write(self, path: Path, data: str) -> None:
        """Write data to path atomically via temp file + os.replace()."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
