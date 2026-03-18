"""Tests for IS-12 Phase 2 artifact_reader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lambertian.postmortem.artifact_reader import read_artifact


# ── helpers ──────────────────────────────────────────────────────────────────


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, records: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    _write_json(tmp_path / "death.json", {
        "instance_id": "test-001",
        "trigger": "max_age",
        "trigger_value": 100.0,
        "threshold_used": 100.0,
        "turn_number": 100,
        "timestamp": "2025-01-15T14:23:45Z",
    })
    _write_json(tmp_path / "manifest.json", {
        "instance_id": "test-001",
        "death_trigger": "max_age",
        "death_timestamp": "2025-01-15T14:23:45Z",
        "harvest_start_time": "2025-01-15T14:23:45Z",
        "harvest_end_time": "2025-01-15T14:23:46Z",
        "harvest_duration_seconds": 1.0,
        "fitness_score": 0.75,
        "artifact_count": 5,
        "failed_artifacts": 0,
        "artifacts": [],
    })
    _write_json(tmp_path / "fitness_postmortem.json", {
        "turn_number": 100,
        "score": 0.75,
        "lifespan": 100,
        "meaningful_event_count": 25,
        "cumulative_pain": 3.5,
        "computed_at": "2025-01-15T14:23:45Z",
    })
    _write_json(tmp_path / "memory" / "working.json", {
        "content": "I fetched some URLs.",
        "updated_turn": 99,
        "updated_at": "2025-01-15T14:23:40Z",
    })
    events = [
        {"event_type": "STARTUP", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:00Z",
         "turn_number": 0, "source_service": "agent"},
        {"event_type": "TOOL_CALL", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:01Z",
         "turn_number": 1, "source_service": "agent"},
        {"event_type": "TOOL_CALL", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:02Z",
         "turn_number": 2, "source_service": "agent"},
        {"event_type": "MEMORY_WRITE", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:03Z",
         "turn_number": 3, "source_service": "agent"},
        {"event_type": "COMPLIANCE_BLOCK", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:04Z",
         "turn_number": 4, "source_service": "agent"},
        {"event_type": "ADAPTATION_DETECTED", "instance_id": "test-001", "timestamp": "2025-01-15T14:00:05Z",
         "turn_number": 5, "source_service": "agent",
         "adaptation_class": "REVIEWED_ADAPTATION", "target_layer": "SELF_MODEL",
         "evidence_excerpt": "I am now more curious"},
    ]
    _write_jsonl(tmp_path / "event_stream" / "events.jsonl", events)
    pain_events = [
        {"event_id": "abc", "incident_type": "tool_failure", "severity": 0.5,
         "description": "Tool failed", "turn_number": 10, "submitted_at": "2025-01-15T14:10:00Z",
         "context": None},
    ]
    _write_jsonl(tmp_path / "pain" / "pain_history.jsonl", pain_events)
    stress_events = [
        {"scalar": 0.3, "raw_last": 0.3, "cpu_pressure_last": 0.2, "memory_pressure_last": 0.4,
         "consecutive_above_death_threshold": 0, "last_sampled_at": "2025-01-15T14:00:00Z"},
        {"scalar": 0.7, "raw_last": 0.7, "cpu_pressure_last": 0.6, "memory_pressure_last": 0.8,
         "consecutive_above_death_threshold": 0, "last_sampled_at": "2025-01-15T14:10:00Z"},
        {"scalar": 0.5, "raw_last": 0.5, "cpu_pressure_last": 0.4, "memory_pressure_last": 0.6,
         "consecutive_above_death_threshold": 0, "last_sampled_at": "2025-01-15T14:20:00Z"},
    ]
    _write_jsonl(tmp_path / "pain" / "stress_history.jsonl", stress_events)
    return tmp_path


# ── tests ─────────────────────────────────────────────────────────────────────


def test_read_artifact_death(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.death is not None
    assert data.death.instance_id == "test-001"
    assert data.death.trigger == "max_age"
    assert data.death.turn_number == 100
    assert data.death.trigger_value == pytest.approx(100.0)


def test_read_artifact_manifest(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.manifest is not None
    assert data.manifest.fitness_score == pytest.approx(0.75)
    assert data.manifest.artifact_count == 5
    assert data.manifest.failed_artifacts == 0
    assert data.manifest.death_trigger == "max_age"


def test_read_artifact_fitness(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.fitness is not None
    assert data.fitness.score == pytest.approx(0.75)
    assert data.fitness.lifespan == 100
    assert data.fitness.meaningful_event_count == 25
    assert data.fitness.cumulative_pain == pytest.approx(3.5)


def test_read_artifact_working_memory(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.working_memory is not None
    assert data.working_memory.content == "I fetched some URLs."
    assert data.working_memory.updated_turn == 99


def test_read_artifact_events_counts(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.events is not None
    assert data.events.total_events == 6
    assert data.events.unique_event_types == 5
    assert data.events.tool_call_count == 2
    assert data.events.memory_write_count == 1
    assert data.events.compliance_block_count == 1


def test_read_artifact_events_startup_timestamp(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.events is not None
    assert data.events.startup_timestamp == "2025-01-15T14:00:00Z"


def test_read_artifact_events_adaptation_entries(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.events is not None
    assert len(data.events.adaptation_entries) == 1
    entry = data.events.adaptation_entries[0]
    assert entry.adaptation_class == "REVIEWED_ADAPTATION"
    assert entry.target_layer == "SELF_MODEL"
    assert entry.turn_number == 5


def test_read_artifact_pain(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.pain is not None
    assert data.pain.pain_event_count == 1
    assert data.pain.peak_stress_scalar == pytest.approx(0.7)
    assert data.pain.pain_entries[0].incident_type == "tool_failure"


def test_read_artifact_death_record_raw(artifact_dir: Path) -> None:
    data = read_artifact(artifact_dir)
    assert data.death_record_raw is not None
    assert "test-001" in data.death_record_raw


def test_read_artifact_missing_files(tmp_path: Path) -> None:
    data = read_artifact(tmp_path)
    assert data.artifact_dir == tmp_path
    assert data.death is None
    assert data.manifest is None
    assert data.fitness is None
    assert data.working_memory is None
    assert data.events is None
    assert data.pain is None
    assert data.death_record_raw is None


def test_read_artifact_malformed_json(tmp_path: Path) -> None:
    (tmp_path / "death.json").write_text("not valid json", encoding="utf-8")
    data = read_artifact(tmp_path)
    assert data.death is None  # graceful degradation


def test_read_artifact_events_blank_lines_skipped(tmp_path: Path) -> None:
    """Blank lines in JSONL files are silently ignored."""
    event_file = tmp_path / "event_stream" / "events.jsonl"
    event_file.parent.mkdir(parents=True)
    event_file.write_text(
        '\n{"event_type": "STARTUP", "timestamp": "2025-01-01T00:00:00Z", "turn_number": 0}\n\n',
        encoding="utf-8",
    )
    data = read_artifact(tmp_path)
    assert data.events is not None
    assert data.events.total_events == 1


def test_read_artifact_manifest_null_fitness_score(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", {
        "instance_id": "x",
        "death_trigger": "max_age",
        "death_timestamp": "2025-01-01T00:00:00Z",
        "harvest_duration_seconds": 0.5,
        "fitness_score": None,
        "artifact_count": 1,
        "failed_artifacts": 0,
        "artifacts": [],
    })
    data = read_artifact(tmp_path)
    assert data.manifest is not None
    assert data.manifest.fitness_score is None
