"""Frozen dataclasses for IS-8 shared pain channel types crossing package boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PainEvent:
    """A discrete incident-derived pain signal (IS-8.3)."""

    event_id: str
    # one of: tool_failure, retrieval_miss, mcp_rejection,
    # network_error, noop_threshold, compliance_unavailable
    incident_type: str
    severity: float  # 0..1
    description: str
    turn_number: int
    submitted_at: str  # ISO 8601 UTC
    context: Optional[dict[str, str]]  # structured incident metadata


@dataclass(frozen=True)
class StressState:
    """Snapshot of the stress scalar computation state (IS-8.2)."""

    scalar: float
    raw_last: float
    cpu_pressure_last: float
    memory_pressure_last: float
    consecutive_above_death_threshold: int
    last_sampled_at: str  # ISO 8601 UTC


@dataclass(frozen=True)
class DeathRecord:
    """Written once on instance death (IS-8.2.5)."""

    instance_id: str
    # one of: stress_sustained, pain_event_critical, max_age
    trigger: str
    trigger_value: float
    threshold_used: float
    turn_number: int
    timestamp: str  # ISO 8601 UTC


@dataclass(frozen=True)
class PainMessage:
    """A formatted pain message ready for injection into the agent prompt (IS-8.5)."""

    channel: str  # "stress" or "event"
    severity: float
    urgency: str  # "notice", "interrupt", or "critical"
    description: str
    context: Optional[str]  # optional single-line context string for event channel
