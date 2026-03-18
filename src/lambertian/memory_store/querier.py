"""Memory querier protocol and stub. IS-10 placeholder."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryQuerier(Protocol):
    def query_episodic(self, text: str, top_k: int) -> list[str]: ...
    def write_episodic(self, content: str, metadata: dict[str, str]) -> str: ...


class NoOpMemoryQuerier:
    """Stub implementation for when Chroma is unavailable."""

    def query_episodic(self, text: str, top_k: int) -> list[str]:
        return []

    def write_episodic(self, content: str, metadata: dict[str, str]) -> str:
        return "noop-" + content[:8]
