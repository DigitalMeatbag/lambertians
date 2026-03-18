"""IS-10.5 memory-worthiness criterion."""
from __future__ import annotations

import re

from lambertian.memory_store.episodic_store import EpisodicStore

_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\d{3}\s+\w[\w\s]*$"),  # HTTP status like "200 OK"
    re.compile(r"^not.?found$", re.IGNORECASE),
    re.compile(r"^none$", re.IGNORECASE),
    re.compile(r"^null$", re.IGNORECASE),
]


class WorthinessChecker:
    """Determines if content is memory-worthy. IS-10.5."""

    _MIN_LENGTH = 80

    def __init__(self, episodic_store: EpisodicStore, min_retrieval_score: float) -> None:
        self._store = episodic_store
        self._min_score = min_retrieval_score

    def is_worthy(self, content: str, document_type: str) -> bool:
        """IS-10.5 three-rule check."""
        # Rule 1: minimum length
        if len(content) < self._MIN_LENGTH:
            return False

        # Rule 2: non-repetitive (similarity to last-written below threshold)
        similarity = self._store.check_last_written_similarity(content)
        if similarity >= self._min_score:
            return False

        # Rule 3: pure tool-result echo guard
        if document_type == "tool_result" and self._is_pure_echo(content):
            return False

        return True

    def _is_pure_echo(self, content: str) -> bool:
        """Returns True if content is a meaningless tool-result echo."""
        stripped = content.strip()
        if not stripped:
            return True
        for pattern in _NOISE_PATTERNS:
            if pattern.match(stripped):
                return True
        return False
