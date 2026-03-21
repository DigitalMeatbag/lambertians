"""Unit tests for DeathGuard — each D4 trigger independently, no-op second write."""

from __future__ import annotations

import json
from pathlib import Path

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
    PolicyConfig,
    TurnConfig,
    UniverseConfig,
)
from lambertian.contracts.pain_records import PainEvent
from lambertian.pain_monitor.death_guard import DeathGuard


def _make_config(max_age_turns: int = 1000) -> Config:
    events = PainEventsConfig(
        scale_min=0.0, scale_max=1.0, queue_max_length=128, fade_turns=5,
        interrupt_threshold=0.65, critical_threshold=0.95,
        default_tool_failure_severity=0.55, default_retrieval_miss_severity=0.35,
        default_mcp_rejection_severity=0.70, default_loop_coherence_failure_severity=0.85,
        default_noop_severity=0.40,
    )
    stress = PainStressConfig(
        scale_min=0.0, scale_max=1.0, sample_interval_seconds=5, ema_alpha=0.2,
        interrupt_threshold=0.70, death_threshold=0.90, death_consecutive_turns=3,
        recovery_threshold=0.60, cpu_weight=0.60, memory_weight=0.40,
        cgroup_blend_weight=0.50,
    )
    return Config(
        universe=UniverseConfig(
            phase="phase1", instance_count=1, instance_id="test-001",
            max_age_turns=max_age_turns, startup_grace_seconds=15,
            normal_shutdown_grace_seconds=5,
        ),
        model=ModelConfig(
            provider="ollama", name="phi4", endpoint_url="http://localhost",
            request_timeout_seconds=90, context_window_tokens=16384,
            max_output_tokens=2048, temperature=0.6, top_p=0.9,
            requires_mid_turn_system_injection=True,
        ),
        eos=EosConfig(
            label="Four Rules", rule_1="r1", rule_2="r2", rule_3="r3", rule_4="r4",
            self_prompting_enabled=True, recency_window_turns=12,
            recency_penalty_weight=0.35, minimum_novelty_score=0.20,
        ),
        turn=TurnConfig(
            loop_sleep_seconds=1.0, max_tool_calls_per_turn=8, max_context_events=32,
            max_pain_messages_per_turn=3, self_prompt_retry_limit=2,
            max_consecutive_noop_turns=3,
            max_consecutive_reflection_turns=5,
        ),
        mcp=McpConfig(
            request_timeout_seconds=30, retry_count=0,
            emit_pain_on_failure=True, emit_pain_on_rejection=True,
        ),
        pain=PainConfig(stress=stress, events=events),
        memory=MemoryConfig(
            working_max_items=32, working_max_chars=2048, working_summary_refresh_turns=8,
            episodic_enabled=True, episodic_max_writes_per_turn=3, episodic_top_k_retrieval=5,
            embedding_provider="ollama", embedding_model="nomic-embed-text",
            minimum_retrieval_score=0.25, self_prompt_similarity_threshold=0.85,
            narrative_enabled=False, semantic_enabled=False, character_enabled=False,
        ),
        event_stream=EventStreamConfig(
            enabled=True, flush_interval_seconds=1, max_file_size_mb=64,
            max_archives=5, log_tool_results=True, log_reviewed_adaptations=True,
        ),
        compliance=ComplianceConfig(
            enabled=True, block_on_violation=True, flag_borderline_cases=True,
            borderline_score_min=0.40, block_score_threshold=0.70,
            emit_pain_event_on_block=True, service_port=8082, service_host="eos-compliance",
        ),
        graveyard=GraveyardConfig(
            enabled=True, artifact_format="json", include_episodic_memory=True,
            include_event_stream=True, include_stress_history=True,
            include_pain_event_history=True, compression_enabled=False,
        ),
        fitness=FitnessConfig(
            enabled=True, active_function="phase1_baseline",
            compute_running_score=True, compute_postmortem_score=True,
            expected_events_per_100_turns=25.0, normalized_pain_baseline=10.0,
            minimum_denominator=0.10,
            quality=FitnessQualityConfig(
                primary_weight=1.0,
                repetition_weight=0.1,
                expected_quality_score=500.0,
            ),
        ),
        paths=PathsConfig(
            runtime_root="runtime", event_stream_file="runtime/events.jsonl",
            memory_root="runtime/memory", pain_root="runtime/pain",
            graveyard_root="runtime/graveyard",
            fitness_file="runtime/fitness/current.json",
            self_model_file="runtime/self/self_model.json",
        ),
        creator_observability=CreatorObservabilityConfig(
            live_reviewed_adaptations=True, live_compliance_blocks=True,
            live_running_fitness=True, read_graveyard_artifacts=True,
        ),
        env_monitor=EnvMonitorConfig(
            update_interval_seconds=10,
            output_path="runtime/env/host_state.json",
        ),
        instance=InstanceConfig(
            constitution_path="config/instance_constitution.md",
        ),
        policy=PolicyConfig(
            response_excerpt_max_chars=500,
            tool_result_summary_max_chars=150,
            working_memory_excerpt_max_chars=400,
            suppression_threshold=3,
            repetition_detection_window=3,
            rolling_context_extraction_count=5,
        ),
    )


def test_check_max_age_below_limit(tmp_path: Path) -> None:
    config = _make_config(max_age_turns=1000)
    guard = DeathGuard(config, tmp_path / "death.json")
    assert guard.check_max_age(999) is False
    assert not (tmp_path / "death.json").exists()


def test_check_max_age_at_limit(tmp_path: Path) -> None:
    config = _make_config(max_age_turns=1000)
    guard = DeathGuard(config, tmp_path / "death.json")
    assert guard.check_max_age(1000) is True
    assert (tmp_path / "death.json").exists()
    record = json.loads((tmp_path / "death.json").read_text())
    assert record["trigger"] == "max_age"
    assert record["turn_number"] == 1000


def test_check_max_age_above_limit(tmp_path: Path) -> None:
    config = _make_config(max_age_turns=1000)
    guard = DeathGuard(config, tmp_path / "death.json")
    assert guard.check_max_age(1001) is True


def test_check_sustained_stress_below_threshold(tmp_path: Path) -> None:
    config = _make_config()
    guard = DeathGuard(config, tmp_path / "death.json")
    # scalar < death_threshold (0.90)
    assert guard.check_sustained_stress(0.85, 10) is False


def test_check_sustained_stress_not_enough_consecutive(tmp_path: Path) -> None:
    config = _make_config()  # death_consecutive_turns=3
    guard = DeathGuard(config, tmp_path / "death.json")
    # scalar >= 0.90 but only 2 consecutive turns
    assert guard.check_sustained_stress(0.92, 2) is False


def test_check_sustained_stress_triggers(tmp_path: Path) -> None:
    config = _make_config()
    guard = DeathGuard(config, tmp_path / "death.json")
    assert guard.check_sustained_stress(0.92, 3) is True
    assert (tmp_path / "death.json").exists()
    record = json.loads((tmp_path / "death.json").read_text())
    assert record["trigger"] == "stress_sustained"


def test_check_critical_event_below_threshold(tmp_path: Path) -> None:
    config = _make_config()  # critical_threshold=0.95
    guard = DeathGuard(config, tmp_path / "death.json")
    event = PainEvent(
        event_id="e1", incident_type="tool_failure", severity=0.94,
        description="Almost critical.", turn_number=5,
        submitted_at="2024-01-01T00:00:00+00:00", context=None,
    )
    assert guard.check_critical_event(event) is False


def test_check_critical_event_triggers(tmp_path: Path) -> None:
    config = _make_config()
    guard = DeathGuard(config, tmp_path / "death.json")
    event = PainEvent(
        event_id="e1", incident_type="tool_failure", severity=0.97,
        description="Critical event.", turn_number=5,
        submitted_at="2024-01-01T00:00:00+00:00", context=None,
    )
    assert guard.check_critical_event(event) is True
    record = json.loads((tmp_path / "death.json").read_text())
    assert record["trigger"] == "pain_event_critical"


def test_second_write_is_noop(tmp_path: Path) -> None:
    """First-declared-cause wins — second write attempt must not overwrite."""
    config = _make_config(max_age_turns=1000)
    death_path = tmp_path / "death.json"
    guard = DeathGuard(config, death_path)
    guard.check_max_age(1000)
    first_content = death_path.read_text()

    # Trigger a different cause — should be silently ignored.
    guard.check_sustained_stress(0.95, 10)
    second_content = death_path.read_text()
    assert first_content == second_content

