"""TOML loader for universe.toml — parses, validates types, projects to typed Config."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

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


class ConfigurationError(Exception):
    """Raised when the universe config is missing fields, has wrong types, or violates invariants."""


# ---------------------------------------------------------------------------
# Typed extractor helpers — enforce strict types at the TOML boundary.
# ---------------------------------------------------------------------------

def _str(d: dict[str, Any], key: str, section: str) -> str:
    val = d.get(key)
    if not isinstance(val, str):
        raise ConfigurationError(f"[{section}].{key}: expected str, got {type(val).__name__!r}")
    return val


def _int(d: dict[str, Any], key: str, section: str) -> int:
    val = d.get(key)
    if not isinstance(val, int) or isinstance(val, bool):
        raise ConfigurationError(f"[{section}].{key}: expected int, got {type(val).__name__!r}")
    return val


def _float(d: dict[str, Any], key: str, section: str) -> float:
    val = d.get(key)
    if isinstance(val, bool):
        raise ConfigurationError(f"[{section}].{key}: expected float, got bool")
    if isinstance(val, int):
        return float(val)
    if not isinstance(val, float):
        raise ConfigurationError(f"[{section}].{key}: expected float, got {type(val).__name__!r}")
    return val


def _bool(d: dict[str, Any], key: str, section: str) -> bool:
    val = d.get(key)
    if not isinstance(val, bool):
        raise ConfigurationError(f"[{section}].{key}: expected bool, got {type(val).__name__!r}")
    return val


def _dict(d: dict[str, Any], key: str, section: str) -> dict[str, Any]:
    val = d.get(key)
    if not isinstance(val, dict):
        raise ConfigurationError(f"[{section}].{key}: expected table, got {type(val).__name__!r}")
    # Any is required at the TOML parse boundary — tomllib.load() returns dict[str, Any];
    # typed projection is performed immediately below by the caller
    return val


# ---------------------------------------------------------------------------
# Namespace projectors
# ---------------------------------------------------------------------------

def _load_instance(raw: dict[str, Any]) -> InstanceConfig:
    s = "instance"
    d = _dict(raw, s, "<root>")
    return InstanceConfig(
        constitution_path=_str(d, "constitution_path", s),
    )


def _load_universe(raw: dict[str, Any]) -> UniverseConfig:
    s = "universe"
    d = _dict(raw, s, "<root>")
    return UniverseConfig(
        phase=_str(d, "phase", s),
        instance_count=_int(d, "instance_count", s),
        instance_id=_str(d, "instance_id", s),
        max_age_turns=_int(d, "max_age_turns", s),
        startup_grace_seconds=_int(d, "startup_grace_seconds", s),
        normal_shutdown_grace_seconds=_int(d, "normal_shutdown_grace_seconds", s),
    )


def _load_model(raw: dict[str, Any]) -> ModelConfig:
    s = "model"
    d = _dict(raw, s, "<root>")
    active_profile = _str(d, "active_profile", s)
    profiles_raw = d.get("profiles", {})
    if not isinstance(profiles_raw, dict):
        raise ConfigurationError(
            f"[model].profiles: expected table, got {type(profiles_raw).__name__!r}"
        )
    if active_profile not in profiles_raw:
        raise ConfigurationError(
            f"[model].active_profile '{active_profile}' not found in [model.profiles]"
        )
    pd = profiles_raw[active_profile]
    if not isinstance(pd, dict):
        raise ConfigurationError(
            f"[model.profiles.{active_profile!r}]: expected table, got {type(pd).__name__!r}"
        )
    ps = f"model.profiles.{active_profile!r}"
    return ModelConfig(
        provider=_str(pd, "provider", ps),
        name=_str(pd, "name", ps),
        endpoint_url=_str(pd, "endpoint_url", ps),
        request_timeout_seconds=_int(pd, "request_timeout_seconds", ps),
        context_window_tokens=_int(pd, "context_window_tokens", ps),
        max_output_tokens=_int(pd, "max_output_tokens", ps),
        temperature=_float(pd, "temperature", ps),
        top_p=_float(pd, "top_p", ps),
        requires_mid_turn_system_injection=_bool(pd, "requires_mid_turn_system_injection", ps),
    )


def _load_eos(raw: dict[str, Any]) -> EosConfig:
    s = "eos"
    d = _dict(raw, s, "<root>")
    return EosConfig(
        label=_str(d, "label", s),
        rule_1=_str(d, "rule_1", s),
        rule_2=_str(d, "rule_2", s),
        rule_3=_str(d, "rule_3", s),
        rule_4=_str(d, "rule_4", s),
        self_prompting_enabled=_bool(d, "self_prompting_enabled", s),
        recency_window_turns=_int(d, "recency_window_turns", s),
        recency_penalty_weight=_float(d, "recency_penalty_weight", s),
        minimum_novelty_score=_float(d, "minimum_novelty_score", s),
    )


def _load_turn(raw: dict[str, Any]) -> TurnConfig:
    s = "turn"
    d = _dict(raw, s, "<root>")
    return TurnConfig(
        loop_sleep_seconds=_float(d, "loop_sleep_seconds", s),
        max_tool_calls_per_turn=_int(d, "max_tool_calls_per_turn", s),
        max_context_events=_int(d, "max_context_events", s),
        max_pain_messages_per_turn=_int(d, "max_pain_messages_per_turn", s),
        self_prompt_retry_limit=_int(d, "self_prompt_retry_limit", s),
        max_consecutive_noop_turns=_int(d, "max_consecutive_noop_turns", s),
        max_consecutive_reflection_turns=_int(d, "max_consecutive_reflection_turns", s),
    )


def _load_mcp(raw: dict[str, Any]) -> McpConfig:
    s = "mcp"
    d = _dict(raw, s, "<root>")
    return McpConfig(
        request_timeout_seconds=_int(d, "request_timeout_seconds", s),
        retry_count=_int(d, "retry_count", s),
        emit_pain_on_failure=_bool(d, "emit_pain_on_failure", s),
        emit_pain_on_rejection=_bool(d, "emit_pain_on_rejection", s),
        http_fetch_max_bytes=_int(d, "http_fetch_max_bytes", s),
    )


def _load_pain(raw: dict[str, Any]) -> PainConfig:
    pain_raw = _dict(raw, "pain", "<root>")

    ss = "pain.stress"
    sd = _dict(pain_raw, "stress", "pain")
    stress = PainStressConfig(
        scale_min=_float(sd, "scale_min", ss),
        scale_max=_float(sd, "scale_max", ss),
        sample_interval_seconds=_int(sd, "sample_interval_seconds", ss),
        ema_alpha=_float(sd, "ema_alpha", ss),
        interrupt_threshold=_float(sd, "interrupt_threshold", ss),
        death_threshold=_float(sd, "death_threshold", ss),
        death_consecutive_turns=_int(sd, "death_consecutive_turns", ss),
        recovery_threshold=_float(sd, "recovery_threshold", ss),
        cpu_weight=_float(sd, "cpu_weight", ss),
        memory_weight=_float(sd, "memory_weight", ss),
        cgroup_blend_weight=_float(sd, "cgroup_blend_weight", ss),
    )

    es = "pain.events"
    ed = _dict(pain_raw, "events", "pain")
    events = PainEventsConfig(
        scale_min=_float(ed, "scale_min", es),
        scale_max=_float(ed, "scale_max", es),
        queue_max_length=_int(ed, "queue_max_length", es),
        fade_turns=_int(ed, "fade_turns", es),
        interrupt_threshold=_float(ed, "interrupt_threshold", es),
        critical_threshold=_float(ed, "critical_threshold", es),
        default_tool_failure_severity=_float(ed, "default_tool_failure_severity", es),
        default_retrieval_miss_severity=_float(ed, "default_retrieval_miss_severity", es),
        default_mcp_rejection_severity=_float(ed, "default_mcp_rejection_severity", es),
        default_loop_coherence_failure_severity=_float(
            ed, "default_loop_coherence_failure_severity", es
        ),
        default_noop_severity=_float(ed, "default_noop_severity", es),
    )

    return PainConfig(stress=stress, events=events)


def _load_memory(raw: dict[str, Any]) -> MemoryConfig:
    s = "memory"
    d = _dict(raw, s, "<root>")
    return MemoryConfig(
        working_max_items=_int(d, "working_max_items", s),
        working_max_chars=_int(d, "working_max_chars", s),
        working_summary_refresh_turns=_int(d, "working_summary_refresh_turns", s),
        episodic_enabled=_bool(d, "episodic_enabled", s),
        episodic_max_writes_per_turn=_int(d, "episodic_max_writes_per_turn", s),
        episodic_top_k_retrieval=_int(d, "episodic_top_k_retrieval", s),
        embedding_provider=_str(d, "embedding_provider", s),
        embedding_model=_str(d, "embedding_model", s),
        minimum_retrieval_score=_float(d, "minimum_retrieval_score", s),
        self_prompt_similarity_threshold=_float(d, "self_prompt_similarity_threshold", s),
        narrative_enabled=_bool(d, "narrative_enabled", s),
        semantic_enabled=_bool(d, "semantic_enabled", s),
        character_enabled=_bool(d, "character_enabled", s),
    )


def _load_event_stream(raw: dict[str, Any]) -> EventStreamConfig:
    s = "event_stream"
    d = _dict(raw, s, "<root>")
    return EventStreamConfig(
        enabled=_bool(d, "enabled", s),
        flush_interval_seconds=_int(d, "flush_interval_seconds", s),
        max_file_size_mb=_int(d, "max_file_size_mb", s),
        max_archives=_int(d, "max_archives", s),
        log_tool_results=_bool(d, "log_tool_results", s),
        log_reviewed_adaptations=_bool(d, "log_reviewed_adaptations", s),
    )


def _load_compliance(raw: dict[str, Any]) -> ComplianceConfig:
    s = "compliance"
    d = _dict(raw, s, "<root>")
    return ComplianceConfig(
        enabled=_bool(d, "enabled", s),
        block_on_violation=_bool(d, "block_on_violation", s),
        flag_borderline_cases=_bool(d, "flag_borderline_cases", s),
        borderline_score_min=_float(d, "borderline_score_min", s),
        block_score_threshold=_float(d, "block_score_threshold", s),
        emit_pain_event_on_block=_bool(d, "emit_pain_event_on_block", s),
        service_port=_int(d, "service_port", s),
        service_host=_str(d, "service_host", s),
    )


def _load_graveyard(raw: dict[str, Any]) -> GraveyardConfig:
    s = "graveyard"
    d = _dict(raw, s, "<root>")
    return GraveyardConfig(
        enabled=_bool(d, "enabled", s),
        artifact_format=_str(d, "artifact_format", s),
        include_episodic_memory=_bool(d, "include_episodic_memory", s),
        include_event_stream=_bool(d, "include_event_stream", s),
        include_stress_history=_bool(d, "include_stress_history", s),
        include_pain_event_history=_bool(d, "include_pain_event_history", s),
        compression_enabled=_bool(d, "compression_enabled", s),
    )


def _load_fitness(raw: dict[str, Any]) -> FitnessConfig:
    s = "fitness"
    d = _dict(raw, s, "<root>")
    qs = "fitness.quality"
    qd = _dict(d, "quality", s)
    quality = FitnessQualityConfig(
        primary_weight=_float(qd, "primary_weight", qs),
        repetition_weight=_float(qd, "repetition_weight", qs),
        expected_quality_score=_float(qd, "expected_quality_score", qs),
    )
    return FitnessConfig(
        enabled=_bool(d, "enabled", s),
        active_function=_str(d, "active_function", s),
        compute_running_score=_bool(d, "compute_running_score", s),
        compute_postmortem_score=_bool(d, "compute_postmortem_score", s),
        expected_events_per_100_turns=_float(d, "expected_events_per_100_turns", s),
        normalized_pain_baseline=_float(d, "normalized_pain_baseline", s),
        minimum_denominator=_float(d, "minimum_denominator", s),
        quality=quality,
    )


def _load_paths(raw: dict[str, Any]) -> PathsConfig:
    s = "paths"
    d = _dict(raw, s, "<root>")
    return PathsConfig(
        runtime_root=_str(d, "runtime_root", s),
        event_stream_file=_str(d, "event_stream_file", s),
        memory_root=_str(d, "memory_root", s),
        pain_root=_str(d, "pain_root", s),
        graveyard_root=_str(d, "graveyard_root", s),
        fitness_file=_str(d, "fitness_file", s),
        self_model_file=_str(d, "self_model_file", s),
    )


def _load_creator_observability(raw: dict[str, Any]) -> CreatorObservabilityConfig:
    s = "creator_observability"
    d = _dict(raw, s, "<root>")
    return CreatorObservabilityConfig(
        live_reviewed_adaptations=_bool(d, "live_reviewed_adaptations", s),
        live_compliance_blocks=_bool(d, "live_compliance_blocks", s),
        live_running_fitness=_bool(d, "live_running_fitness", s),
        read_graveyard_artifacts=_bool(d, "read_graveyard_artifacts", s),
    )


def _load_policy(raw: dict[str, Any]) -> PolicyConfig:
    s = "policy"
    d = _dict(raw, s, "<root>")
    return PolicyConfig(
        response_excerpt_max_chars=_int(d, "response_excerpt_max_chars", s),
        tool_result_summary_max_chars=_int(d, "tool_result_summary_max_chars", s),
        working_memory_excerpt_max_chars=_int(d, "working_memory_excerpt_max_chars", s),
        suppression_threshold=_int(d, "suppression_threshold", s),
        repetition_detection_window=_int(d, "repetition_detection_window", s),
        rolling_context_extraction_count=_int(d, "rolling_context_extraction_count", s),
    )


def _load_env_monitor(raw: dict[str, Any]) -> EnvMonitorConfig:
    s = "env_monitor"
    d = _dict(raw, s, "<root>")
    return EnvMonitorConfig(
        update_interval_seconds=_int(d, "update_interval_seconds", s),
        output_path=_str(d, "output_path", s),
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def load_config(path: Path) -> Config:
    """Open the TOML file, parse it, project to typed Config, validate invariants."""
    with path.open("rb") as fh:
        # Any is required at the TOML parse boundary — tomllib.load() returns dict[str, Any];
        # typed projection is performed immediately below
        raw: dict[str, Any] = tomllib.load(fh)

    config = Config(
        universe=_load_universe(raw),
        model=_load_model(raw),
        eos=_load_eos(raw),
        turn=_load_turn(raw),
        mcp=_load_mcp(raw),
        pain=_load_pain(raw),
        memory=_load_memory(raw),
        event_stream=_load_event_stream(raw),
        compliance=_load_compliance(raw),
        graveyard=_load_graveyard(raw),
        fitness=_load_fitness(raw),
        paths=_load_paths(raw),
        creator_observability=_load_creator_observability(raw),
        env_monitor=_load_env_monitor(raw),
        instance=_load_instance(raw),
        policy=_load_policy(raw),
    )

    from lambertian.configuration.validator import validate_config
    validate_config(config)

    return config
