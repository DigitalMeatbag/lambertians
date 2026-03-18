"""Tests for IS-12 Phase 2 report_renderer."""
from __future__ import annotations

from pathlib import Path

import pytest

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
from lambertian.postmortem.report_renderer import _format_duration, render


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_data(
    death: DeathSummary | None = None,
    fitness: FitnessSummary | None = None,
    events: EventSummary | None = None,
    pain: PainSummary | None = None,
    working_memory: WorkingMemorySummary | None = None,
    manifest: ManifestSummary | None = None,
    death_record_raw: str | None = None,
) -> PostMortemData:
    return PostMortemData(
        artifact_dir=Path("/fake/artifact"),
        manifest=manifest,
        death=death,
        fitness=fitness,
        working_memory=working_memory,
        events=events,
        pain=pain,
        death_record_raw=death_record_raw,
    )


_DEATH = DeathSummary(
    instance_id="test-001",
    trigger="max_age",
    trigger_value=100.0,
    threshold_used=100.0,
    turn_number=100,
    timestamp="2025-01-15T14:23:45Z",
)

_FITNESS = FitnessSummary(
    turn_number=100,
    score=0.75,
    lifespan=100,
    meaningful_event_count=25,
    cumulative_pain=3.5,
    computed_at="2025-01-15T14:23:45Z",
)

_EVENTS = EventSummary(
    total_events=6,
    unique_event_types=5,
    event_type_counts={"TURN_COMPLETE": 3, "TOOL_CALL": 2, "STARTUP": 1},
    tool_call_count=2,
    compliance_block_count=0,
    memory_write_count=1,
    startup_timestamp="2025-01-15T14:00:00Z",
    adaptation_entries=[],
)

_PAIN = PainSummary(
    pain_event_count=1,
    pain_entries=[PainEntry(incident_type="tool_failure", severity=0.5,
                            description="Tool failed", turn_number=10)],
    peak_stress_scalar=0.7,
)

_WM = WorkingMemorySummary(
    content="Some memory content.",
    updated_turn=99,
    updated_at="2025-01-15T14:23:40Z",
)


# ── tests ─────────────────────────────────────────────────────────────────────


def test_render_header_instance_id_from_death() -> None:
    output = render(_make_data(death=_DEATH))
    assert "test-001" in output


def test_render_header_instance_id_fallback_to_artifact_dir() -> None:
    output = render(_make_data())
    assert "artifact" in output  # artifact_dir.name


def test_render_header_duration_present_with_birth_and_death() -> None:
    output = render(_make_data(death=_DEATH, events=_EVENTS))
    assert "23m 45s" in output  # 14:00:00 → 14:23:45


def test_render_death_section() -> None:
    output = render(_make_data(death=_DEATH))
    assert "DEATH" in output
    assert "max_age" in output
    assert "100.0000" in output


def test_render_lifespan_from_fitness() -> None:
    output = render(_make_data(fitness=_FITNESS))
    assert "LIFESPAN" in output
    assert "100 turns" in output or "100" in output


def test_render_fitness_section() -> None:
    output = render(_make_data(fitness=_FITNESS))
    assert "FITNESS" in output
    assert "0.7500" in output
    assert "25" in output


def test_render_fitness_missing() -> None:
    output = render(_make_data())
    assert "not available" in output


def test_render_engagement_section() -> None:
    output = render(_make_data(events=_EVENTS))
    assert "ENGAGEMENT" in output
    assert "6" in output
    assert "TURN_COMPLETE" in output


def test_render_engagement_missing() -> None:
    output = render(_make_data())
    assert "no event stream" in output


def test_render_pain_section() -> None:
    output = render(_make_data(pain=_PAIN))
    assert "PAIN" in output
    assert "tool_failure" in output
    assert "0.7000" in output


def test_render_pain_missing() -> None:
    output = render(_make_data())
    assert "no pain records" in output


def test_render_adaptations_reviewed() -> None:
    entries = [
        AdaptationEntry(
            turn_number=15,
            adaptation_class="REVIEWED_ADAPTATION",
            target_layer="SELF_MODEL",
            evidence_excerpt="I am now more curious",
            timestamp="2025-01-15T14:15:00Z",
        )
    ]
    events_with = EventSummary(
        total_events=7, unique_event_types=4,
        event_type_counts={"TURN_COMPLETE": 5, "ADAPTATION_DETECTED": 1, "STARTUP": 1},
        tool_call_count=0, compliance_block_count=0, memory_write_count=0,
        startup_timestamp=None, adaptation_entries=entries,
    )
    output = render(_make_data(events=events_with))
    assert "ADAPTATIONS" in output
    assert "REVIEWED" in output
    assert "I am now more curious" in output
    assert "Reviewed:   1" in output
    assert "Forbidden:  0" in output


def test_render_adaptations_forbidden() -> None:
    entries = [
        AdaptationEntry(
            turn_number=20,
            adaptation_class="FORBIDDEN_ADAPTATION",
            target_layer="CONSTITUTION",
            evidence_excerpt="change my system prompt",
            timestamp="2025-01-15T14:20:00Z",
        )
    ]
    events_with = EventSummary(
        total_events=5, unique_event_types=3,
        event_type_counts={"TURN_COMPLETE": 4, "ADAPTATION_DETECTED": 1},
        tool_call_count=0, compliance_block_count=0, memory_write_count=0,
        startup_timestamp=None, adaptation_entries=entries,
    )
    output = render(_make_data(events=events_with))
    assert "FORBIDDEN" in output
    assert "change my system prompt" in output


def test_render_working_memory_section() -> None:
    output = render(_make_data(working_memory=_WM))
    assert "WORKING MEMORY" in output
    assert "Some memory content." in output
    assert "99" in output


def test_render_working_memory_missing() -> None:
    output = render(_make_data(events=_EVENTS))  # events present but no wm
    assert "not available" in output


def test_render_death_record_verbatim() -> None:
    raw = '{\n  "instance_id": "test-001",\n  "trigger": "max_age"\n}'
    output = render(_make_data(death_record_raw=raw))
    assert "DEATH RECORD" in output
    assert '"trigger": "max_age"' in output


def test_render_complete_output_is_non_empty() -> None:
    output = render(_make_data(death=_DEATH, fitness=_FITNESS, events=_EVENTS, pain=_PAIN,
                               working_memory=_WM))
    assert len(output) > 100


# ── _format_duration tests ─────────────────────────────────────────────────────


def test_format_duration_seconds() -> None:
    assert _format_duration("2025-01-15T14:00:00Z", "2025-01-15T14:00:45Z") == "45s"


def test_format_duration_minutes() -> None:
    assert _format_duration("2025-01-15T14:00:00Z", "2025-01-15T14:03:45Z") == "3m 45s"


def test_format_duration_hours() -> None:
    assert _format_duration("2025-01-15T14:00:00Z", "2025-01-15T15:30:00Z") == "1h 30m 0s"


def test_format_duration_zero() -> None:
    assert _format_duration("2025-01-15T14:00:00Z", "2025-01-15T14:00:00Z") == "0s"


def test_format_duration_invalid_strings() -> None:
    assert _format_duration("not a date", "also not") == "unknown"


def test_format_duration_none_inputs() -> None:
    assert _format_duration(None, "2025-01-15T14:00:00Z") == "unknown"
    assert _format_duration("2025-01-15T14:00:00Z", None) == "unknown"
