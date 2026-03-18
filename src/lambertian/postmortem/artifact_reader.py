"""IS-12 Phase 2 — reads graveyard artifact directories into structured models."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from lambertian.postmortem.models import (
    AdaptationEntry,
    DeathSummary,
    EventSummary,
    FitnessSummary,
    ManifestSummary,
    PainEntry,
    PainSummary,
    PostMortemData,
    WorkingMemorySummary,
)

_log = logging.getLogger(__name__)


def read_artifact(artifact_dir: Path) -> PostMortemData:
    """Read all available artifacts from a graveyard artifact directory."""
    return PostMortemData(
        artifact_dir=artifact_dir,
        manifest=_read_manifest(artifact_dir),
        death=_read_death(artifact_dir),
        fitness=_read_fitness(artifact_dir),
        working_memory=_read_working_memory(artifact_dir),
        events=_read_events(artifact_dir),
        pain=_read_pain(artifact_dir),
        death_record_raw=_read_raw_text(artifact_dir / "death.json"),
    )


def _load_json(path: Path) -> Optional[dict[str, Any]]:
    # Any: JSON deserialization — structure is unknown at parse time; callers coerce all fields explicitly.
    if not path.exists():
        return None
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            _log.warning("Expected JSON object in %s, got %s", path, type(raw).__name__)
            return None
        return raw  # type: ignore[return-value]
    except json.JSONDecodeError as exc:
        _log.warning("Malformed JSON in %s: %s", path, exc)
        return None


def _read_raw_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_manifest(artifact_dir: Path) -> Optional[ManifestSummary]:
    data = _load_json(artifact_dir / "manifest.json")
    if data is None:
        return None
    raw_score = data.get("fitness_score")
    fitness_score: Optional[float] = float(raw_score) if raw_score is not None else None
    return ManifestSummary(
        instance_id=str(data.get("instance_id", "")),
        death_trigger=str(data.get("death_trigger", "")),
        death_timestamp=str(data.get("death_timestamp", "")),
        harvest_duration_seconds=float(data.get("harvest_duration_seconds", 0.0)),
        fitness_score=fitness_score,
        artifact_count=int(data.get("artifact_count", 0)),
        failed_artifacts=int(data.get("failed_artifacts", 0)),
    )


def _read_death(artifact_dir: Path) -> Optional[DeathSummary]:
    data = _load_json(artifact_dir / "death.json")
    if data is None:
        return None
    return DeathSummary(
        instance_id=str(data.get("instance_id", "")),
        trigger=str(data.get("trigger", "")),
        trigger_value=float(data.get("trigger_value", 0.0)),
        threshold_used=float(data.get("threshold_used", 0.0)),
        turn_number=int(data.get("turn_number", 0)),
        timestamp=str(data.get("timestamp", "")),
    )


def _read_fitness(artifact_dir: Path) -> Optional[FitnessSummary]:
    data = _load_json(artifact_dir / "fitness_postmortem.json")
    if data is None:
        return None
    return FitnessSummary(
        turn_number=int(data.get("turn_number", 0)),
        score=float(data.get("score", 0.0)),
        lifespan=int(data.get("lifespan", 0)),
        meaningful_event_count=int(data.get("meaningful_event_count", 0)),
        cumulative_pain=float(data.get("cumulative_pain", 0.0)),
        computed_at=str(data.get("computed_at", "")),
    )


def _read_working_memory(artifact_dir: Path) -> Optional[WorkingMemorySummary]:
    data = _load_json(artifact_dir / "memory" / "working.json")
    if data is None:
        return None
    return WorkingMemorySummary(
        content=str(data.get("content", "")),
        updated_turn=int(data.get("updated_turn", 0)),
        updated_at=str(data.get("updated_at", "")),
    )


def _read_events(artifact_dir: Path) -> Optional[EventSummary]:
    event_file = artifact_dir / "event_stream" / "events.jsonl"
    if not event_file.exists():
        return None

    event_type_counts: dict[str, int] = {}
    startup_timestamp: Optional[str] = None
    tool_call_count = 0
    compliance_block_count = 0
    memory_write_count = 0
    adaptation_entries: list[AdaptationEntry] = []

    for raw_line in event_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event: Any = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = str(event.get("event_type", "UNKNOWN"))
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        if event_type == "STARTUP":
            startup_timestamp = str(event.get("timestamp", ""))
        elif event_type == "TOOL_CALL":
            tool_call_count += 1
        elif event_type == "COMPLIANCE_BLOCK":
            compliance_block_count += 1
        elif event_type == "MEMORY_WRITE":
            memory_write_count += 1
        elif event_type == "ADAPTATION_DETECTED":
            adaptation_entries.append(
                AdaptationEntry(
                    turn_number=int(event.get("turn_number", 0)),
                    adaptation_class=str(event.get("adaptation_class", "")),
                    target_layer=str(event.get("target_layer", "")),
                    evidence_excerpt=str(event.get("evidence_excerpt", "")),
                    timestamp=str(event.get("timestamp", "")),
                )
            )

    return EventSummary(
        total_events=sum(event_type_counts.values()),
        unique_event_types=len(event_type_counts),
        event_type_counts=event_type_counts,
        tool_call_count=tool_call_count,
        compliance_block_count=compliance_block_count,
        memory_write_count=memory_write_count,
        startup_timestamp=startup_timestamp,
        adaptation_entries=adaptation_entries,
    )


def _read_pain(artifact_dir: Path) -> Optional[PainSummary]:
    pain_file = artifact_dir / "pain" / "pain_history.jsonl"
    stress_file = artifact_dir / "pain" / "stress_history.jsonl"

    if not pain_file.exists() and not stress_file.exists():
        return None

    pain_entries: list[PainEntry] = []
    if pain_file.exists():
        for raw_line in pain_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                event: Any = json.loads(line)
                pain_entries.append(
                    PainEntry(
                        incident_type=str(event.get("incident_type", "")),
                        severity=float(event.get("severity", 0.0)),
                        description=str(event.get("description", "")),
                        turn_number=int(event.get("turn_number", 0)),
                    )
                )
            except (json.JSONDecodeError, ValueError):
                continue

    peak_stress = 0.0
    if stress_file.exists():
        for raw_line in stress_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                snapshot: Any = json.loads(line)
                scalar = float(snapshot.get("scalar", 0.0))
                if scalar > peak_stress:
                    peak_stress = scalar
            except (json.JSONDecodeError, ValueError):
                continue

    return PainSummary(
        pain_event_count=len(pain_entries),
        pain_entries=pain_entries,
        peak_stress_scalar=peak_stress,
    )
