"""Chroma-backed episodic memory store. IS-10.4."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import chromadb
import httpx
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from lambertian.configuration.universe_config import Config
from lambertian.memory_store.retrieval_result import (
    EpisodicDocument,
    MemoryRetrievalResult,
    MemoryWriteRequest,
)

_log = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot: float = sum(x * y for x, y in zip(a, b))
    norm_a: float = sum(x * x for x in a) ** 0.5
    norm_b: float = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """Calls Ollama /api/embed to produce embeddings for Chroma.

    Ollama >= 0.1.26 uses /api/embed (plural inputs, response key "embeddings").
    The old /api/embeddings endpoint was removed in 0.18.x.
    """

    def __init__(self, ollama_base_url: str, model_name: str) -> None:
        self._base_url = ollama_base_url
        self._model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        # /api/embed accepts a list of strings and returns all embeddings at once.
        response = httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model_name, "input": list(input)},
            timeout=60.0,
        )
        response.raise_for_status()
        data: Any = response.json()  # Any: httpx json() returns Any
        raw_embeddings: list[list[Any]] = data["embeddings"]
        return [[float(x) for x in emb] for emb in raw_embeddings]


class EpisodicStore:
    """Chroma-backed episodic memory. IS-10.4."""

    _COLLECTION_NAME = "episodic"

    def __init__(self, config: Config, ollama_base_url: str) -> None:
        self._config = config
        self._embed_fn = OllamaEmbeddingFunction(
            ollama_base_url=ollama_base_url,
            model_name=config.memory.embedding_model,
        )
        client = chromadb.HttpClient(host="chroma", port=8000)
        # Do not pass embedding_function — we embed at the application layer and pass
        # embeddings= / query_embeddings= explicitly.  Letting chromadb manage embeddings
        # causes np.float32 type-check failures across library version boundaries.
        self._collection = client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def write(
        self,
        request: MemoryWriteRequest,
        instance_id: str,
        stress_state_path: Path,
    ) -> str:
        """Embed content, build metadata, store in Chroma. Returns document_id."""
        doc_id = f"{instance_id}-t{request.turn_number}-{request.write_index}"
        pain_score = self._read_pain_score(stress_state_path)
        metadata: dict[str, str | int | float | bool] = {
            "instance_id": instance_id,
            "turn_number": request.turn_number,
            "document_type": request.document_type,
            "tool_name": request.tool_name or "",
            "adaptation_class": request.adaptation_class or "",
            "pain_score_at_write": pain_score,
            "written_at": datetime.now(timezone.utc).isoformat(),
        }
        self._collection.add(
            ids=[doc_id],
            documents=[request.content],
            embeddings=[self._embed_text(request.content)],
            metadatas=[metadata],
        )
        return doc_id

    def _embed_text(self, text: str) -> list[float]:
        """Embed a single string via Ollama, returning plain Python floats."""
        raw: list[object] = list(self._embed_fn([text])[0])
        return [float(x) for x in raw]

    def query(
        self, query_text: str, top_k: int, min_score: float
    ) -> MemoryRetrievalResult:
        """Query by semantic similarity. Returns MemoryRetrievalResult."""
        embedding: list[float] = self._embed_text(query_text)
        result: Any = self._collection.query(  # Any: chromadb QueryResult is loosely typed
            query_embeddings=[embedding],  # type: ignore[arg-type]  # list[list[float]] at chromadb query boundary
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )
        ids: list[str] = result["ids"][0] if result.get("ids") else []
        raw_distances: Any = result.get("distances")
        distances: list[float] = list(raw_distances[0]) if raw_distances else []
        raw_docs: Any = result.get("documents")
        docs: list[str] = list(raw_docs[0]) if raw_docs else []
        raw_metas: Any = result.get("metadatas")
        metas: list[dict[str, object]] = list(raw_metas[0]) if raw_metas else []

        documents: list[EpisodicDocument] = []
        for doc_id, distance, content, meta in zip(ids, distances, docs, metas):
            # Chroma cosine distance range [0, 2]: 0=identical, 2=opposite
            # Convert to similarity in [0, 1]
            similarity = 1.0 - float(distance) / 2.0
            if similarity >= min_score:
                documents.append(
                    EpisodicDocument(
                        document_id=doc_id,
                        content=content,
                        metadata=meta,
                        similarity_score=similarity,
                    )
                )

        return MemoryRetrievalResult(
            documents=documents,
            retrieval_miss=len(documents) == 0,
        )

    def check_last_written_similarity(self, content: str) -> float:
        """For worthiness check: cosine similarity of content to last-written doc. IS-10.5."""
        peek: Any = self._collection.peek(limit=1)  # Any: chromadb GetResult is loosely typed
        raw_embeddings: Any = peek.get("embeddings")
        if raw_embeddings is None or len(raw_embeddings) == 0:
            return 0.0
        stored_emb: list[float] = [float(x) for x in raw_embeddings[0]]
        content_emb: list[float] = self._embed_text(content)
        return _cosine_similarity(content_emb, stored_emb)

    def get_document(self, document_id: str) -> Optional[EpisodicDocument]:
        """Fetch a single document by ID. Returns None if not found."""
        try:
            result: Any = self._collection.get(
                ids=[document_id],
                include=["documents", "metadatas"],
            )
        except Exception:
            return None
        ids: list[str] = result.get("ids", [])
        if not ids:
            return None
        docs: list[str] = result.get("documents", [])
        metas: list[dict[str, object]] = result.get("metadatas", [])
        return EpisodicDocument(
            document_id=ids[0],
            content=docs[0] if docs else "",
            metadata=metas[0] if metas else {},
            similarity_score=1.0,
        )

    def update_metadata(
        self, document_id: str, metadata_updates: dict[str, str | int | float | bool]
    ) -> bool:
        """Merge metadata_updates into an existing document's metadata. Returns True if doc existed."""
        existing = self.get_document(document_id)
        if existing is None:
            return False
        merged = dict(existing.metadata)
        merged.update(metadata_updates)
        self._collection.update(
            ids=[document_id],
            metadatas=[merged],
        )
        return True

    def clear_collection(self) -> None:
        """Delete and recreate the episodic collection, clearing all lifetime memory.

        Delete-and-recreate is cleaner than bulk document deletion and preserves
        the metadata configuration. Called by the graveyard after artifact harvest.
        """
        count: int = self._collection.count()
        if count == 0:
            _log.info(
                "Episodic collection '%s' clear: no-op (collection already empty)",
                self._COLLECTION_NAME,
            )
            return

        client = chromadb.HttpClient(host="chroma", port=8000)
        client.delete_collection(self._COLLECTION_NAME)
        self._collection = client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        _log.info(
            "Episodic collection '%s' cleared: %d documents removed",
            self._COLLECTION_NAME,
            count,
        )


    def _read_pain_score(self, stress_state_path: Path) -> float:
        """Read stress_scalar from stress_state.json. Returns 0.0 if absent/unreadable."""
        if not stress_state_path.exists():
            return 0.0
        try:
            raw: Any = json.loads(  # Any: json.loads returns Any
                stress_state_path.read_text(encoding="utf-8")
            )
            return float(raw["scalar"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return 0.0
