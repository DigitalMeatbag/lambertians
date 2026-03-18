"""IS-12.4 Artifact collector — harvests runtime artifacts on instance death."""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lambertian.configuration.universe_config import Config

_log = logging.getLogger(__name__)


@dataclass
class HarvestArtifact:
    source: str
    output: str  # relative to output_dir
    success: bool
    error: Optional[str]


class ArtifactCollector:
    """IS-12.4. Collects harvest artifacts. Partial failure is logged, not fatal."""

    def __init__(self, config: Config, runtime_base: Path) -> None:
        self._config = config
        self._runtime_base = runtime_base

    def collect_all(self, output_dir: Path) -> list[HarvestArtifact]:
        """Execute all configured artifact collections."""
        artifacts: list[HarvestArtifact] = []
        artifacts.extend(self._collect_death_record(output_dir))
        if self._config.graveyard.include_event_stream:
            artifacts.extend(self._collect_event_stream(output_dir))
        if self._config.graveyard.include_pain_event_history:
            artifacts.extend(self._collect_pain_history(output_dir))
        if self._config.graveyard.include_stress_history:
            artifacts.extend(self._collect_stress_history(output_dir))
        artifacts.extend(self._collect_memory_snapshot(output_dir))
        if self._config.graveyard.include_episodic_memory:
            artifacts.extend(self._collect_episodic_memory_export(output_dir))
        return artifacts

    def _copy_file(self, src: Path, dst: Path, output_dir: Path) -> HarvestArtifact:
        """Copy src to dst. Creates parent dirs."""
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return HarvestArtifact(
                source=str(src),
                output=str(dst.relative_to(output_dir)),
                success=True,
                error=None,
            )
        except Exception as e:
            _log.warning("ArtifactCollector: failed to copy %s → %s: %s", src, dst, e)
            return HarvestArtifact(
                source=str(src),
                output=str(dst.relative_to(output_dir)),
                success=False,
                error=str(e),
            )

    def _collect_death_record(self, output_dir: Path) -> list[HarvestArtifact]:
        src = self._runtime_base / "pain" / "death.json"
        dst = output_dir / "death.json"
        return [self._copy_file(src, dst, output_dir)]

    def _collect_event_stream(self, output_dir: Path) -> list[HarvestArtifact]:
        """Concatenate all events*.jsonl per IS-9.7 sort order into output/event_stream/events.jsonl."""
        event_dir = self._runtime_base / "event_stream"
        try:
            files = sorted(event_dir.glob("events*.jsonl"), key=lambda p: p.name)
            dst = output_dir / "event_stream" / "events.jsonl"
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "wb") as out_f:
                for f in files:
                    try:
                        with open(f, "rb") as in_f:
                            out_f.write(in_f.read())
                    except OSError as e:
                        _log.warning("event_stream collect: skip %s: %s", f, e)
            rel = str(dst.relative_to(output_dir))
            return [HarvestArtifact(source=str(event_dir), output=rel, success=True, error=None)]
        except Exception as e:
            return [
                HarvestArtifact(
                    source=str(self._runtime_base / "event_stream"),
                    output="event_stream/events.jsonl",
                    success=False,
                    error=str(e),
                )
            ]

    def _collect_pain_history(self, output_dir: Path) -> list[HarvestArtifact]:
        src = self._runtime_base / "pain" / "pain_history.jsonl"
        dst = output_dir / "pain" / "pain_history.jsonl"
        return [self._copy_file(src, dst, output_dir)]

    def _collect_stress_history(self, output_dir: Path) -> list[HarvestArtifact]:
        src = self._runtime_base / "pain" / "stress_history.jsonl"
        dst = output_dir / "pain" / "stress_history.jsonl"
        return [self._copy_file(src, dst, output_dir)]

    def _collect_memory_snapshot(self, output_dir: Path) -> list[HarvestArtifact]:
        """Copy all files in runtime/memory/ to output/memory/."""
        memory_dir = Path(self._config.paths.memory_root)
        artifacts: list[HarvestArtifact] = []
        try:
            if not memory_dir.exists():
                return [
                    HarvestArtifact(
                        source=str(memory_dir),
                        output="memory/",
                        success=False,
                        error="memory dir not found",
                    )
                ]
            for src_file in memory_dir.rglob("*"):
                if src_file.is_file():
                    rel = src_file.relative_to(memory_dir)
                    dst = output_dir / "memory" / rel
                    artifacts.append(self._copy_file(src_file, dst, output_dir))
        except Exception as e:
            artifacts.append(
                HarvestArtifact(
                    source=str(memory_dir), output="memory/", success=False, error=str(e)
                )
            )
        return artifacts

    def _collect_episodic_memory_export(self, output_dir: Path) -> list[HarvestArtifact]:
        """Export Chroma episodic collection as JSONL. IS-12.4."""
        dst = output_dir / "memory" / "episodic_export.jsonl"
        try:
            import chromadb
            import json as _json

            memory_root = Path(self._config.paths.memory_root)
            client = chromadb.PersistentClient(path=str(memory_root / "chroma"))
            collection = client.get_collection("episodic")
            results = collection.get(include=["documents", "metadatas"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                # chromadb returns typed containers; cast to object lists for safe iteration
                ids = list(results.get("ids") or [])
                documents = list(results.get("documents") or [])
                metadatas = list(results.get("metadatas") or [])
                for i, doc_id in enumerate(ids):
                    record = {
                        "document_id": doc_id,
                        "content": documents[i] if i < len(documents) else None,
                        "metadata": metadatas[i] if i < len(metadatas) else None,
                    }
                    f.write(_json.dumps(record) + "\n")
            rel = str(dst.relative_to(output_dir))
            return [
                HarvestArtifact(
                    source="chroma:episodic", output=rel, success=True, error=None
                )
            ]
        except Exception as e:
            _log.warning("episodic export failed: %s", e)
            return [
                HarvestArtifact(
                    source="chroma:episodic",
                    output="memory/episodic_export.jsonl",
                    success=False,
                    error=str(e),
                )
            ]
