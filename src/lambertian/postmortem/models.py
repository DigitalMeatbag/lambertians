"""IS-12 Phase 2 — post-mortem artifact models."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DeathSummary:
    instance_id: str
    trigger: str
    trigger_value: float
    threshold_used: float
    turn_number: int
    timestamp: str


@dataclass(frozen=True)
class FitnessSummary:
    turn_number: int
    score: float
    lifespan: int
    meaningful_event_count: int
    cumulative_pain: float
    computed_at: str


@dataclass(frozen=True)
class WorkingMemorySummary:
    content: str
    updated_turn: int
    updated_at: str


@dataclass(frozen=True)
class AdaptationEntry:
    turn_number: int
    adaptation_class: str
    target_layer: str
    evidence_excerpt: str
    timestamp: str


@dataclass(frozen=True)
class EventSummary:
    total_events: int
    unique_event_types: int
    event_type_counts: dict[str, int]
    tool_call_count: int
    compliance_block_count: int
    memory_write_count: int
    startup_timestamp: Optional[str]
    adaptation_entries: list[AdaptationEntry]


@dataclass(frozen=True)
class PainEntry:
    incident_type: str
    severity: float
    description: str
    turn_number: int


@dataclass(frozen=True)
class PainSummary:
    pain_event_count: int
    pain_entries: list[PainEntry]
    peak_stress_scalar: float


@dataclass(frozen=True)
class ManifestSummary:
    instance_id: str
    death_trigger: str
    death_timestamp: str
    harvest_duration_seconds: float
    fitness_score: Optional[float]
    artifact_count: int
    failed_artifacts: int


@dataclass(frozen=True)
class PostMortemData:
    artifact_dir: Path
    manifest: Optional[ManifestSummary]
    death: Optional[DeathSummary]
    fitness: Optional[FitnessSummary]
    working_memory: Optional[WorkingMemorySummary]
    events: Optional[EventSummary]
    pain: Optional[PainSummary]
    death_record_raw: Optional[str]  # verbatim JSON text for display
