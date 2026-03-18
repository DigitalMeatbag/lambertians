"""IS-10.3 self-prompt ring buffer with embeddings."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Callable


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot: float = sum(x * y for x, y in zip(a, b))
    norm_a: float = sum(x * x for x in a) ** 0.5
    norm_b: float = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SelfPromptStore:
    """Ring buffer of recent self-prompts with embeddings. IS-10.3."""

    def __init__(
        self,
        store_path: Path,
        capacity: int,
        embedding_fn: Callable[[str], list[float]],
    ) -> None:
        self._path = store_path
        self._capacity = capacity
        self._embedding_fn = embedding_fn

    def get_recent(self) -> list[dict[str, object]]:
        """Returns list of {"turn_number": N, "content": "...", "embedding": [...]}."""
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            entries: list[dict[str, object]] = []
            for item in raw.get("prompts", []):
                entries.append(
                    {
                        "turn_number": int(item["turn_number"]),
                        "content": str(item["content"]),
                        "embedding": [float(x) for x in item["embedding"]],
                    }
                )
            return entries
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return []

    def append(self, content: str, turn_number: int) -> None:
        """Embed content, append to ring buffer, trim to capacity, write atomically."""
        existing = self.get_recent()
        embedding: list[float] = self._embedding_fn(content)
        existing.append(
            {"turn_number": turn_number, "content": content, "embedding": embedding}
        )
        trimmed = existing[-self._capacity :]
        self._atomic_write(json.dumps({"prompts": trimmed}))

    def compute_max_similarity(self, candidate: str) -> float:
        """Embed candidate, return max cosine similarity to any stored embedding."""
        entries = self.get_recent()
        if not entries:
            return 0.0
        cand_emb: list[float] = self._embedding_fn(candidate)
        max_sim = 0.0
        for entry in entries:
            raw_emb: object = entry["embedding"]
            stored_emb: list[float] = [float(x) for x in raw_emb]  # type: ignore[attr-defined]  # object->float at dict[str, object] boundary
            sim = _cosine_similarity(cand_emb, stored_emb)
            if sim > max_sim:
                max_sim = sim
        return max_sim

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
