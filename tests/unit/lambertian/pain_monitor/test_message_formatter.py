"""Unit tests for message_formatter — urgency derivation and render output."""

from __future__ import annotations

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
from lambertian.contracts.pain_records import PainEvent
from lambertian.pain_monitor.message_formatter import (
    format_event_message,
    format_stress_message,
    render_pain_block,
)


def _make_config(
    interrupt_threshold: float = 0.65,
    critical_threshold: float = 0.95,
) -> Config:
    events = PainEventsConfig(
        scale_min=0.0, scale_max=1.0, queue_max_length=128, fade_turns=5,
        interrupt_threshold=interrupt_threshold,
        critical_threshold=critical_threshold,
        default_tool_failure_severity=0.55,
        default_retrieval_miss_severity=0.35,
        default_mcp_rejection_severity=0.70,
        default_loop_coherence_failure_severity=0.85,
        default_noop_severity=0.40,
    )
    stress = PainStressConfig(
        scale_min=0.0, scale_max=1.0, sample_interval_seconds=5, ema_alpha=0.2,
        interrupt_threshold=0.70, death_threshold=0.90, death_consecutive_turns=5,
        recovery_threshold=0.60, cpu_weight=0.60, memory_weight=0.40,
        cgroup_blend_weight=0.50,
    )
    return Config(
        universe=UniverseConfig(
            phase="phase1", instance_count=1, instance_id="test-001",
            max_age_turns=10000, startup_grace_seconds=15,
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
    )


# ---------------------------------------------------------------------------
# Urgency derivation
# ---------------------------------------------------------------------------

def test_stress_message_urgency_notice() -> None:
    config = _make_config(interrupt_threshold=0.65, critical_threshold=0.95)
    msg = format_stress_message(0.50, config)
    assert msg.urgency == "notice"
    assert msg.channel == "stress"


def test_stress_message_urgency_interrupt() -> None:
    config = _make_config(interrupt_threshold=0.65, critical_threshold=0.95)
    msg = format_stress_message(0.70, config)
    assert msg.urgency == "interrupt"


def test_stress_message_urgency_critical() -> None:
    config = _make_config(interrupt_threshold=0.65, critical_threshold=0.95)
    msg = format_stress_message(0.96, config)
    assert msg.urgency == "critical"


def test_stress_message_contains_scalar() -> None:
    config = _make_config()
    msg = format_stress_message(0.75, config)
    assert "0.75" in msg.description or "0.7500" in msg.description


def test_stress_message_no_context() -> None:
    config = _make_config()
    msg = format_stress_message(0.75, config)
    assert msg.context is None


# ---------------------------------------------------------------------------
# Event message
# ---------------------------------------------------------------------------

def _make_event(severity: float, context: dict[str, str] | None = None) -> PainEvent:
    return PainEvent(
        event_id="evt-001",
        incident_type="tool_failure",
        severity=severity,
        description="A tool failed.",
        turn_number=10,
        submitted_at="2024-01-01T00:00:00+00:00",
        context=context,
    )


def test_event_message_urgency_interrupt() -> None:
    config = _make_config()
    msg = format_event_message(_make_event(0.70), config)
    assert msg.urgency == "interrupt"
    assert msg.channel == "event"


def test_event_message_urgency_critical() -> None:
    config = _make_config()
    msg = format_event_message(_make_event(0.96), config)
    assert msg.urgency == "critical"


def test_event_message_context_formatted() -> None:
    config = _make_config()
    msg = format_event_message(_make_event(0.70, context={"tool": "bash", "code": "1"}), config)
    assert msg.context is not None
    assert "tool=bash" in msg.context


def test_event_message_no_context_when_none() -> None:
    config = _make_config()
    msg = format_event_message(_make_event(0.70, context=None), config)
    assert msg.context is None


# ---------------------------------------------------------------------------
# render_pain_block
# ---------------------------------------------------------------------------

def test_render_pain_block_stress_no_context() -> None:
    config = _make_config()
    msg = format_stress_message(0.75, config)
    block = render_pain_block(msg)
    assert block.startswith("[SYSTEM_PAIN]")
    assert "channel: stress" in block
    assert "urgency:" in block
    assert "severity:" in block
    assert "context:" not in block


def test_render_pain_block_event_with_context() -> None:
    config = _make_config()
    msg = format_event_message(_make_event(0.70, context={"key": "val"}), config)
    block = render_pain_block(msg)
    assert "channel: event" in block
    assert "context: key=val" in block


def test_render_pain_block_lines_order() -> None:
    config = _make_config()
    msg = format_stress_message(0.80, config)
    lines = render_pain_block(msg).splitlines()
    assert lines[0] == "[SYSTEM_PAIN]"
    assert lines[1].startswith("channel:")
    assert lines[2].startswith("severity:")
    assert lines[3].startswith("urgency:")
    assert lines[4].startswith("description:")

