"""Working memory file R/W. IS-10.2."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class WorkingMemoryStore:
    """Reads/writes runtime/memory/working.json. IS-10.2."""

    def __init__(self, memory_dir: Path, max_chars: int) -> None:
        self._path = memory_dir / "working.json"
        self._max_chars = max_chars

    def read(self) -> Optional[str]:
        """Returns content string, or None if absent."""
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return str(raw["content"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None

    def write(self, content: str, turn_number: int) -> None:
        """Truncate to max_chars (tail-first), write atomically with os.replace()."""
        truncated = content[: self._max_chars]
        data = json.dumps(
            {
                "content": truncated,
                "updated_turn": turn_number,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._atomic_write(data)

    def _atomic_write(self, data: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
