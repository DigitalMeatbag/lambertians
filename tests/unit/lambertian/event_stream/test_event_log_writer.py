"""Unit tests for EventLogWriter — IS-9."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from lambertian.configuration.universe_config import (
    ComplianceConfig,
    Config,
    CreatorObservabilityConfig,
    EnvMonitorConfig,
    EosConfig,
    EventStreamConfig,
    FitnessConfig,
    FitnessQualityConfig,
    GraveyardConfig,
    InstanceConfig,
    McpConfig,
    MemoryConfig,
    ModelConfig,
    PainConfig,
    PainEventsConfig,
    PainStressConfig,
    PathsConfig,
    TurnConfig,
    UniverseConfig,
)
from lambertian.event_stream.event_log_writer import EventLogWriteError, EventLogWriter


def _make_config(tmp_path: Path, max_file_size_mb: int = 64, max_archives: int = 3) -> Config:
    events_file = str(tmp_path / "event_stream" / "events.jsonl")
    return Config(
        universe=UniverseConfig(
            phase="phase1",
            instance_count=1,
            instance_id="test-instance-001",
            max_age_turns=1000,
            startup_grace_seconds=5,
            normal_shutdown_grace_seconds=5,
        ),
        model=ModelConfig(
            provider="ollama",
            name="phi4",
            endpoint_url="http://localhost:11434",
            request_timeout_seconds=60,
            context_window_tokens=8192,
            max_output_tokens=2048,
            temperature=0.7,
            top_p=0.9,
            requires_mid_turn_system_injection=False,
        ),
        eos=EosConfig(
            label="Four Rules",
            rule_1="Ya gotta eat",
            rule_2="Don't be a dick",
            rule_3="Don't be a lump",
            rule_4="Do nothing on purpose",
            self_prompting_enabled=True,
            recency_window_turns=12,
            recency_penalty_weight=0.35,
            minimum_novelty_score=0.20,
        ),
        turn=TurnConfig(
            loop_sleep_seconds=1.0,
            max_tool_calls_per_turn=8,
            max_context_events=32,
            max_pain_messages_per_turn=3,
            self_prompt_retry_limit=2,
            max_consecutive_noop_turns=3,
        ),
        mcp=McpConfig(
            request_timeout_seconds=30,
            retry_count=0,
            emit_pain_on_failure=True,
            emit_pain_on_rejection=True,
            http_fetch_max_bytes=65536,
        ),
        pain=PainConfig(
            stress=PainStressConfig(
                scale_min=0.0,
                scale_max=1.0,
                sample_interval_seconds=5,
                ema_alpha=0.20,
                interrupt_threshold=0.70,
                death_threshold=0.90,
                death_consecutive_turns=5,
                recovery_threshold=0.60,
                cpu_weight=0.60,
                memory_weight=0.40,
                cgroup_blend_weight=0.50,
            ),
            events=PainEventsConfig(
                scale_min=0.0,
                scale_max=1.0,
                queue_max_length=128,
                fade_turns=5,
                interrupt_threshold=0.65,
                critical_threshold=0.95,
                default_tool_failure_severity=0.55,
                default_retrieval_miss_severity=0.35,
                default_mcp_rejection_severity=0.70,
                default_loop_coherence_failure_severity=0.85,
                default_noop_severity=0.40,
            ),
        ),
        memory=MemoryConfig(
            working_max_items=32,
            working_max_chars=2048,
            working_summary_refresh_turns=8,
            episodic_enabled=True,
            episodic_max_writes_per_turn=3,
            episodic_top_k_retrieval=5,
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
            minimum_retrieval_score=0.25,
            self_prompt_similarity_threshold=0.85,
            narrative_enabled=False,
            semantic_enabled=False,
            character_enabled=False,
        ),
        event_stream=EventStreamConfig(
            enabled=True,
            flush_interval_seconds=300,  # large so flush only happens when forced
            max_file_size_mb=max_file_size_mb,
            max_archives=max_archives,
            log_tool_results=True,
            log_reviewed_adaptations=True,
        ),
        compliance=ComplianceConfig(
            enabled=True,
            block_on_violation=True,
            flag_borderline_cases=True,
            borderline_score_min=0.40,
            block_score_threshold=0.70,
            emit_pain_event_on_block=True,
            service_port=8082, service_host="eos-compliance",
        ),
        graveyard=GraveyardConfig(
            enabled=True,
            artifact_format="json",
            include_episodic_memory=True,
            include_event_stream=True,
            include_stress_history=True,
            include_pain_event_history=True,
            compression_enabled=False,
        ),
        fitness=FitnessConfig(
            enabled=True,
            active_function="phase1_baseline",
            compute_running_score=True,
            compute_postmortem_score=True,
            expected_events_per_100_turns=25.0,
            normalized_pain_baseline=10.0,
            minimum_denominator=0.10,
            quality=FitnessQualityConfig(
                primary_weight=1.0,
                repetition_weight=0.1,
                expected_quality_score=500.0,
            ),
        ),
        paths=PathsConfig(
            runtime_root=str(tmp_path),
            event_stream_file=events_file,
            memory_root=str(tmp_path / "memory"),
            pain_root=str(tmp_path / "pain"),
            graveyard_root=str(tmp_path / "graveyard"),
            fitness_file=str(tmp_path / "fitness.json"),
            self_model_file=str(tmp_path / "self_model.json"),
        ),
        creator_observability=CreatorObservabilityConfig(
            live_reviewed_adaptations=True,
            live_compliance_blocks=True,
            live_running_fitness=True,
            read_graveyard_artifacts=True,
        ),
        env_monitor=EnvMonitorConfig(
            update_interval_seconds=10,
            output_path="runtime/env/host_state.json",
        ),
        instance=InstanceConfig(
            constitution_path="config/instance_constitution.md",
        ),
    )


def test_write_event_creates_file(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    writer = EventLogWriter(config)
    writer.write_event("TURN_COMPLETE", 1, "turn_engine", {"noop": False})
    writer.close()

    events_file = Path(config.paths.event_stream_file)
    assert events_file.exists()
    line = events_file.read_text(encoding="utf-8").strip()
    record: Any = json.loads(line)
    assert record["event_type"] == "TURN_COMPLETE"
    assert record["turn_number"] == 1
    assert record["source_service"] == "turn_engine"
    assert record["instance_id"] == "test-instance-001"
    assert record["noop"] is False
    assert "event_id" in record
    assert "timestamp" in record


def test_write_multiple_events(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    writer = EventLogWriter(config)
    for i in range(5):
        writer.write_event("TEST_EVENT", i, "svc", {"seq": i})
    writer.close()

    lines = Path(config.paths.event_stream_file).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    records: list[Any] = [json.loads(ln) for ln in lines]
    seqs = [r["seq"] for r in records]
    assert seqs == list(range(5))


def test_critical_event_flushes_immediately(tmp_path: Path) -> None:
    """DEATH_TRIGGER and TURN_FAILED must trigger flush regardless of interval."""
    config = _make_config(tmp_path)
    writer = EventLogWriter(config)

    flush_called: list[str] = []
    original_flush = writer._file.flush  # type: ignore[attr-defined]

    def tracking_flush() -> None:
        flush_called.append("flush")
        original_flush()

    with patch.object(writer._file, "flush", side_effect=tracking_flush):
        writer.write_event("DEATH_TRIGGER", 99, "death_guard", {})

    assert len(flush_called) >= 1
    writer.close()


def test_turn_failed_flushes_immediately(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    writer = EventLogWriter(config)

    flush_called: list[str] = []
    original_flush = writer._file.flush  # type: ignore[attr-defined]

    def tracking_flush() -> None:
        flush_called.append("flush")
        original_flush()

    with patch.object(writer._file, "flush", side_effect=tracking_flush):
        writer.write_event("TURN_FAILED", 5, "turn_engine", {"reason": "error"})

    assert len(flush_called) >= 1
    writer.close()


def test_rotation_at_size_limit(tmp_path: Path) -> None:
    """Rotation should occur when _current_size reaches the limit."""
    config = _make_config(tmp_path, max_file_size_mb=1)
    writer = EventLogWriter(config)

    # Force _current_size to be at the threshold so next write triggers rotation.
    threshold = config.event_stream.max_file_size_mb * 1024 * 1024
    writer._current_size = threshold - 1  # type: ignore[attr-defined]

    writer.write_event("TURN_COMPLETE", 1, "turn_engine", {"data": "x"})
    writer.close()

    base_dir = Path(config.paths.event_stream_file).parent
    archives = sorted(base_dir.glob("events.*.jsonl"))
    assert len(archives) >= 1, "Expected at least one rotated archive"


def test_rotation_archive_pruning(tmp_path: Path) -> None:
    """Archives beyond max_archives should be deleted (oldest first)."""
    max_archives = 2
    config = _make_config(tmp_path, max_file_size_mb=1, max_archives=max_archives)
    writer = EventLogWriter(config)

    # Trigger rotation max_archives + 2 times.
    for _ in range(max_archives + 2):
        threshold = config.event_stream.max_file_size_mb * 1024 * 1024
        writer._current_size = threshold - 1  # type: ignore[attr-defined]
        writer.write_event("TURN_COMPLETE", 1, "turn_engine", {})

    writer.close()

    base_dir = Path(config.paths.event_stream_file).parent
    archives = list(base_dir.glob("events.*.jsonl"))
    assert len(archives) <= max_archives, (
        f"Expected at most {max_archives} archives, found {len(archives)}"
    )


def test_write_failure_raises_event_log_write_error(tmp_path: Path) -> None:
    """I/O failure on write must raise EventLogWriteError."""
    config = _make_config(tmp_path)
    writer = EventLogWriter(config)

    with patch.object(writer._file, "write", side_effect=OSError("disk full")):
        with pytest.raises(EventLogWriteError, match="disk full"):
            writer.write_event("TURN_COMPLETE", 1, "turn_engine", {})

    writer.close()

