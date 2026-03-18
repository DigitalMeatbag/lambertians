"""Writes the self-visible self-model snapshot to the filesystem. IS-5.4 step 4."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from lambertian.configuration.universe_config import Config
from lambertian.self_model.prompt_block_assembler import build_self_model_data


class SelfModelWriter:
    """Writes the self-visible self-model snapshot to runtime/self/self_model.json. IS-5.4 step 4."""

    def __init__(self, config: Config, runtime_self_dir: Path) -> None:
        self._config = config
        self._runtime_self_dir = runtime_self_dir

    def write(self) -> None:
        """Writes self_model.json atomically to runtime_self_dir. Creates dir if needed."""
        self._runtime_self_dir.mkdir(parents=True, exist_ok=True)
        target = self._runtime_self_dir / "self_model.json"
        data = build_self_model_data(self._config)
        payload = json.dumps(data, indent=2)

        # Atomic write: write to a temp file in the same directory, then os.replace().
        fd, tmp_path = tempfile.mkstemp(dir=self._runtime_self_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up temp file on any failure before re-raising.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
