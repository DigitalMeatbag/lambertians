"""Tests for each IS-1.5 cross-field invariant — one violated config per test."""

from __future__ import annotations

import pytest

from lambertian.configuration.loader import ConfigurationError
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
from lambertian.configuration.validator import validate_config


def _make_valid_config(
    *,
    stress: PainStressConfig | None = None,
    events: PainEventsConfig | None = None,
    compliance: ComplianceConfig | None = None,
    fitness: FitnessConfig | None = None,
    universe: UniverseConfig | None = None,
    memory: MemoryConfig | None = None,
) -> Config:
    """Build a minimal valid Config, allowing selective override of nested configs."""
    default_stress = PainStressConfig(
        scale_min=0.0,
        scale_max=1.0,
        sample_interval_seconds=5,
        ema_alpha=0.2,
        interrupt_threshold=0.70,
        death_threshold=0.90,
        death_consecutive_turns=5,
        recovery_threshold=0.60,
        cpu_weight=0.60,
        memory_weight=0.40,
        cgroup_blend_weight=0.50,
    )
    default_events = PainEventsConfig(
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
    )
    default_compliance = ComplianceConfig(
        enabled=True,
        block_on_violation=True,
        flag_borderline_cases=True,
        borderline_score_min=0.40,
        block_score_threshold=0.70,
        emit_pain_event_on_block=True,
        service_port=8082, service_host="eos-compliance",
    )
    default_fitness = FitnessConfig(
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
    )
    default_universe = UniverseConfig(
        phase="phase1",
        instance_count=1,
        instance_id="test-001",
        max_age_turns=10000,
        startup_grace_seconds=15,
        normal_shutdown_grace_seconds=5,
    )
    default_memory = MemoryConfig(
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
    )
    return Config(
        universe=universe or default_universe,
        model=ModelConfig(
            provider="ollama",
            name="phi4",
            endpoint_url="http://ollama:11434",
            request_timeout_seconds=90,
            context_window_tokens=16384,
            max_output_tokens=2048,
            temperature=0.6,
            top_p=0.9,
            requires_mid_turn_system_injection=True,
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
        ),
        pain=PainConfig(stress=stress or default_stress, events=events or default_events),
        memory=memory or default_memory,
        event_stream=EventStreamConfig(
            enabled=True,
            flush_interval_seconds=1,
            max_file_size_mb=64,
            max_archives=5,
            log_tool_results=True,
            log_reviewed_adaptations=True,
        ),
        compliance=compliance or default_compliance,
        graveyard=GraveyardConfig(
            enabled=True,
            artifact_format="json",
            include_episodic_memory=True,
            include_event_stream=True,
            include_stress_history=True,
            include_pain_event_history=True,
            compression_enabled=False,
        ),
        fitness=fitness or default_fitness,
        paths=PathsConfig(
            runtime_root="runtime",
            event_stream_file="runtime/event_stream/events.jsonl",
            memory_root="runtime/memory",
            pain_root="runtime/pain",
            graveyard_root="runtime/graveyard",
            fitness_file="runtime/fitness/current.json",
            self_model_file="runtime/self/self_model.json",
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


def test_valid_config_passes() -> None:
    validate_config(_make_valid_config())


def test_invariant_death_gte_interrupt() -> None:
    stress = PainStressConfig(
        scale_min=0.0, scale_max=1.0, sample_interval_seconds=5, ema_alpha=0.2,
        interrupt_threshold=0.90, death_threshold=0.80,  # death < interrupt — violation
        death_consecutive_turns=5, recovery_threshold=0.50,
        cpu_weight=0.60, memory_weight=0.40, cgroup_blend_weight=0.50,
    )
    with pytest.raises(ConfigurationError, match="death_threshold"):
        validate_config(_make_valid_config(stress=stress))


def test_invariant_critical_gte_interrupt() -> None:
    events = PainEventsConfig(
        scale_min=0.0, scale_max=1.0, queue_max_length=128, fade_turns=5,
        interrupt_threshold=0.90, critical_threshold=0.80,  # critical < interrupt — violation
        default_tool_failure_severity=0.55, default_retrieval_miss_severity=0.35,
        default_mcp_rejection_severity=0.70, default_loop_coherence_failure_severity=0.85,
        default_noop_severity=0.40,
    )
    with pytest.raises(ConfigurationError, match="critical_threshold"):
        validate_config(_make_valid_config(events=events))


def test_invariant_recovery_lt_death() -> None:
    stress = PainStressConfig(
        scale_min=0.0, scale_max=1.0, sample_interval_seconds=5, ema_alpha=0.2,
        interrupt_threshold=0.70, death_threshold=0.90,
        death_consecutive_turns=5,
        recovery_threshold=0.90,  # equal to death — violation
        cpu_weight=0.60, memory_weight=0.40, cgroup_blend_weight=0.50,
    )
    with pytest.raises(ConfigurationError, match="recovery_threshold"):
        validate_config(_make_valid_config(stress=stress))


def test_invariant_weights_sum_to_one() -> None:
    stress = PainStressConfig(
        scale_min=0.0, scale_max=1.0, sample_interval_seconds=5, ema_alpha=0.2,
        interrupt_threshold=0.70, death_threshold=0.90,
        death_consecutive_turns=5, recovery_threshold=0.60,
        cpu_weight=0.50, memory_weight=0.40,  # sum = 0.90 — violation
        cgroup_blend_weight=0.50,
    )
    with pytest.raises(ConfigurationError, match="cpu_weight"):
        validate_config(_make_valid_config(stress=stress))


def test_invariant_block_score_gt_borderline() -> None:
    compliance = ComplianceConfig(
        enabled=True, block_on_violation=True, flag_borderline_cases=True,
        borderline_score_min=0.70,
        block_score_threshold=0.70,  # equal — violation
        emit_pain_event_on_block=True, service_port=8082, service_host="eos-compliance",
    )
    with pytest.raises(ConfigurationError, match="block_score_threshold"):
        validate_config(_make_valid_config(compliance=compliance))


def test_invariant_minimum_denominator_positive() -> None:
    fitness = FitnessConfig(
        enabled=True, active_function="phase1_baseline",
        compute_running_score=True, compute_postmortem_score=True,
        expected_events_per_100_turns=25.0, normalized_pain_baseline=10.0,
        minimum_denominator=0.0,  # zero — violation
        quality=FitnessQualityConfig(primary_weight=1.0, repetition_weight=0.1, expected_quality_score=500.0),
    )
    with pytest.raises(ConfigurationError, match="minimum_denominator"):
        validate_config(_make_valid_config(fitness=fitness))


def test_invariant_phase1_instance_count() -> None:
    universe = UniverseConfig(
        phase="phase1", instance_count=2,  # > 1 — violation
        instance_id="test-001", max_age_turns=10000,
        startup_grace_seconds=15, normal_shutdown_grace_seconds=5,
    )
    with pytest.raises(ConfigurationError, match="instance_count"):
        validate_config(_make_valid_config(universe=universe))


def test_invariant_phase1_narrative_disabled() -> None:
    memory = MemoryConfig(
        working_max_items=32, working_max_chars=2048, working_summary_refresh_turns=8,
        episodic_enabled=True, episodic_max_writes_per_turn=3, episodic_top_k_retrieval=5,
        embedding_provider="ollama", embedding_model="nomic-embed-text",
        minimum_retrieval_score=0.25, self_prompt_similarity_threshold=0.85,
        narrative_enabled=True,  # enabled — violation
        semantic_enabled=False, character_enabled=False,
    )
    with pytest.raises(ConfigurationError, match="narrative_enabled"):
        validate_config(_make_valid_config(memory=memory))


def test_invariant_quality_primary_weight_positive() -> None:
    fitness = FitnessConfig(
        enabled=True, active_function="phase2_quality_weighted",
        compute_running_score=True, compute_postmortem_score=True,
        expected_events_per_100_turns=25.0, normalized_pain_baseline=10.0,
        minimum_denominator=0.10,
        quality=FitnessQualityConfig(
            primary_weight=0.0,  # zero — violation
            repetition_weight=0.1,
            expected_quality_score=500.0,
        ),
    )
    with pytest.raises(ConfigurationError, match="primary_weight"):
        validate_config(_make_valid_config(fitness=fitness))


def test_invariant_quality_repetition_weight_non_negative() -> None:
    fitness = FitnessConfig(
        enabled=True, active_function="phase2_quality_weighted",
        compute_running_score=True, compute_postmortem_score=True,
        expected_events_per_100_turns=25.0, normalized_pain_baseline=10.0,
        minimum_denominator=0.10,
        quality=FitnessQualityConfig(
            primary_weight=1.0,
            repetition_weight=-0.1,  # negative — violation
            expected_quality_score=500.0,
        ),
    )
    with pytest.raises(ConfigurationError, match="repetition_weight"):
        validate_config(_make_valid_config(fitness=fitness))


def test_invariant_quality_expected_quality_score_positive() -> None:
    fitness = FitnessConfig(
        enabled=True, active_function="phase2_quality_weighted",
        compute_running_score=True, compute_postmortem_score=True,
        expected_events_per_100_turns=25.0, normalized_pain_baseline=10.0,
        minimum_denominator=0.10,
        quality=FitnessQualityConfig(
            primary_weight=1.0,
            repetition_weight=0.1,
            expected_quality_score=0.0,  # zero — violation
        ),
    )
    with pytest.raises(ConfigurationError, match="expected_quality_score"):
        validate_config(_make_valid_config(fitness=fitness))

