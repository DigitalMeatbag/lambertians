"""Memory querier protocol, NoOp stub, and Chroma-backed implementation. IS-10."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from lambertian.configuration.universe_config import Config
from lambertian.memory_store.episodic_store import EpisodicStore
from lambertian.memory_store.retrieval_result import MemoryWriteRequest
from lambertian.memory_store.worthiness import WorthinessChecker


@runtime_checkable
class MemoryQuerier(Protocol):
    def query_episodic(self, text: str, top_k: int) -> list[str]: ...
    def write_episodic(self, content: str, metadata: dict[str, str]) -> str: ...
    def write_episodic_worthy(
        self, request: MemoryWriteRequest, instance_id: str
    ) -> str: ...


class NoOpMemoryQuerier:
    """Stub implementation for when Chroma is unavailable."""

    def query_episodic(self, text: str, top_k: int) -> list[str]:
        return []

    def write_episodic(self, content: str, metadata: dict[str, str]) -> str:
        return "noop-" + content[:8]

    def write_episodic_worthy(
        self, request: MemoryWriteRequest, instance_id: str
    ) -> str:
        return ""


class ChromaMemoryQuerier:
    """Full Chroma-backed implementation. IS-10.4."""

    def __init__(
        self,
        episodic_store: EpisodicStore,
        config: Config,
        stress_state_path: Path,
    ) -> None:
        self._store = episodic_store
        self._config = config
        self._stress_state_path = stress_state_path

    def query_episodic(self, text: str, top_k: int) -> list[str]:
        """Query and return content strings of retrieved documents."""
        result = self._store.query(
            text, top_k, self._config.memory.minimum_retrieval_score
        )
        if result.retrieval_miss:
            return []
        return [doc.content for doc in result.documents]

    def write_episodic(self, content: str, metadata: dict[str, str]) -> str:
        """Simple write interface satisfying MemoryQuerier Protocol."""
        try:
            turn_number = int(metadata.get("turn", "0"))
        except ValueError:
            turn_number = 0
        request = MemoryWriteRequest(
            content=content,
            document_type=metadata.get("document_type", "model_response"),
            turn_number=turn_number,
            write_index=0,
            tool_name=metadata.get("tool_name") or None,
            adaptation_class=metadata.get("adaptation_class") or None,
        )
        instance_id = metadata.get("instance_id", "")
        return self._store.write(request, instance_id, self._stress_state_path)

    def write_episodic_worthy(
        self,
        request: MemoryWriteRequest,
        instance_id: str,
    ) -> str:
        """Write with worthiness check. Returns document_id or '' if not worthy."""
        checker = WorthinessChecker(
            self._store, self._config.memory.minimum_retrieval_score
        )
        if not checker.is_worthy(request.content, request.document_type):
            return ""
        return self._store.write(request, instance_id, self._stress_state_path)
