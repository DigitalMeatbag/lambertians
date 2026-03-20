"""Frozen dataclasses for all 14 IS-1 configuration namespaces."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InstanceConfig:
    constitution_path: str


@dataclass(frozen=True)
class UniverseConfig:
    phase: str
    instance_count: int
    instance_id: str
    max_age_turns: int
    startup_grace_seconds: int
    normal_shutdown_grace_seconds: int


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    name: str
    endpoint_url: str
    request_timeout_seconds: int
    context_window_tokens: int
    max_output_tokens: int
    temperature: float
    top_p: float
    requires_mid_turn_system_injection: bool


@dataclass(frozen=True)
class EosConfig:
    label: str
    rule_1: str
    rule_2: str
    rule_3: str
    rule_4: str
    self_prompting_enabled: bool
    recency_window_turns: int
    recency_penalty_weight: float
    minimum_novelty_score: float


@dataclass(frozen=True)
class TurnConfig:
    loop_sleep_seconds: float
    max_tool_calls_per_turn: int
    max_context_events: int
    max_pain_messages_per_turn: int
    self_prompt_retry_limit: int
    max_consecutive_noop_turns: int
    max_consecutive_reflection_turns: int


@dataclass(frozen=True)
class McpConfig:
    request_timeout_seconds: int
    retry_count: int
    emit_pain_on_failure: bool
    emit_pain_on_rejection: bool
    # [ASSUMED: 65536 (64 KB) — IS-7 requires truncation limit; no value specified in IS-1]
    http_fetch_max_bytes: int = field(default=65536)


@dataclass(frozen=True)
class PainStressConfig:
    scale_min: float
    scale_max: float
    sample_interval_seconds: int
    ema_alpha: float
    interrupt_threshold: float
    death_threshold: float
    death_consecutive_turns: int
    recovery_threshold: float
    cpu_weight: float
    memory_weight: float
    cgroup_blend_weight: float


@dataclass(frozen=True)
class PainEventsConfig:
    scale_min: float
    scale_max: float
    queue_max_length: int
    fade_turns: int
    interrupt_threshold: float
    critical_threshold: float
    default_tool_failure_severity: float
    default_retrieval_miss_severity: float
    default_mcp_rejection_severity: float
    default_loop_coherence_failure_severity: float
    default_noop_severity: float


@dataclass(frozen=True)
class PainConfig:
    stress: PainStressConfig
    events: PainEventsConfig


@dataclass(frozen=True)
class MemoryConfig:
    working_max_items: int
    working_max_chars: int
    working_summary_refresh_turns: int
    episodic_enabled: bool
    episodic_max_writes_per_turn: int
    episodic_top_k_retrieval: int
    embedding_provider: str
    embedding_model: str
    minimum_retrieval_score: float
    self_prompt_similarity_threshold: float
    narrative_enabled: bool
    semantic_enabled: bool
    character_enabled: bool


@dataclass(frozen=True)
class EventStreamConfig:
    enabled: bool
    flush_interval_seconds: int
    max_file_size_mb: int
    max_archives: int
    log_tool_results: bool
    log_reviewed_adaptations: bool


@dataclass(frozen=True)
class ComplianceConfig:
    enabled: bool
    block_on_violation: bool
    flag_borderline_cases: bool
    borderline_score_min: float
    block_score_threshold: float
    emit_pain_event_on_block: bool
    service_port: int
    service_host: str


@dataclass(frozen=True)
class GraveyardConfig:
    enabled: bool
    artifact_format: str
    include_episodic_memory: bool
    include_event_stream: bool
    include_stress_history: bool
    include_pain_event_history: bool
    compression_enabled: bool


@dataclass(frozen=True)
class FitnessQualityConfig:
    primary_weight: float
    repetition_weight: float
    expected_quality_score: float


@dataclass(frozen=True)
class FitnessConfig:
    enabled: bool
    active_function: str
    compute_running_score: bool
    compute_postmortem_score: bool
    expected_events_per_100_turns: float
    normalized_pain_baseline: float
    minimum_denominator: float
    quality: FitnessQualityConfig


@dataclass(frozen=True)
class PathsConfig:
    runtime_root: str
    event_stream_file: str
    memory_root: str
    pain_root: str
    graveyard_root: str
    fitness_file: str
    self_model_file: str


@dataclass(frozen=True)
class CreatorObservabilityConfig:
    live_reviewed_adaptations: bool
    live_compliance_blocks: bool
    live_running_fitness: bool
    read_graveyard_artifacts: bool


@dataclass(frozen=True)
class EnvMonitorConfig:
    update_interval_seconds: int
    output_path: str


@dataclass(frozen=True)
class Config:
    universe: UniverseConfig
    model: ModelConfig
    eos: EosConfig
    turn: TurnConfig
    mcp: McpConfig
    pain: PainConfig
    memory: MemoryConfig
    event_stream: EventStreamConfig
    compliance: ComplianceConfig
    graveyard: GraveyardConfig
    fitness: FitnessConfig
    paths: PathsConfig
    creator_observability: CreatorObservabilityConfig
    env_monitor: EnvMonitorConfig
    instance: InstanceConfig
