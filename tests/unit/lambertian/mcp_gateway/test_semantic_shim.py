"""Unit tests for SemanticShimRegistry. IS-7."""

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
    TurnConfig,
    UniverseConfig,
)
from lambertian.mcp_gateway.semantic_shim import (
    AliasShim,
    SemanticShimRegistry,
    ShimKind,
    VirtualShim,
    build_shim_registry,
    generate_agent_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    model_name: str = "qwen2.5:32b",
) -> Config:
    """Build a full Config for tests, with tmp_path-based memory root."""
    memory_root = tmp_path / "memory"
    memory_root.mkdir(exist_ok=True)
    return Config(
        universe=UniverseConfig(
            phase="phase2",
            instance_count=1,
            instance_id="test-shim-001",
            max_age_turns=500,
            startup_grace_seconds=15,
            normal_shutdown_grace_seconds=5,
        ),
        model=ModelConfig(
            provider="ollama",
            name=model_name,
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
            http_fetch_max_bytes=100,
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
            flush_interval_seconds=1,
            max_file_size_mb=64,
            max_archives=5,
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
            service_port=8082,
            service_host="eos-compliance",
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
            runtime_root=str(tmp_path / "runtime"),
            event_stream_file=str(tmp_path / "events" / "events.jsonl"),
            memory_root=str(memory_root),
            pain_root=str(tmp_path / "pain"),
            graveyard_root=str(tmp_path / "graveyard"),
            fitness_file=str(tmp_path / "fitness" / "current.json"),
            self_model_file=str(tmp_path / "self" / "self_model.json"),
        ),
        creator_observability=CreatorObservabilityConfig(
            live_reviewed_adaptations=True,
            live_compliance_blocks=True,
            live_running_fitness=True,
            read_graveyard_artifacts=True,
        ),
        env_monitor=EnvMonitorConfig(
            update_interval_seconds=10,
            output_path=str(tmp_path / "env" / "host_state.json"),
        ),
        instance=InstanceConfig(
            constitution_path="config/instance_constitution.md",
        ),
    )


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    (memory_root / "turn_state.json").write_text('{"turn_number": 42}')
    (memory_root / "working.json").write_text('{"content": "thinking about trees"}')
    return _make_config(tmp_path)


@pytest.fixture()
def registry(config: Config) -> SemanticShimRegistry:
    read_shims: dict[str, AliasShim | VirtualShim] = {
        "self/identity": AliasShim("runtime/agent-work/self/identity.md"),
        "memory/working": AliasShim("runtime/memory/working.json"),
        "/proc/self/status": VirtualShim("agent_status"),
    }
    list_shims = {
        "self": AliasShim("runtime/agent-work/self"),
        "journal": AliasShim("runtime/agent-work/journal"),
    }
    return SemanticShimRegistry(
        read_shims=read_shims,
        list_shims=list_shims,
        virtual_generators={"agent_status": generate_agent_status},
        config=config,
    )


# ---------------------------------------------------------------------------
# Read shim tests
# ---------------------------------------------------------------------------


class TestReadAlias:
    def test_alias_rewrites_path(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("self/identity")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self/identity.md"
        assert result.original_path == "self/identity"

    def test_alias_content_is_none(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("self/identity")
        assert result is not None
        assert result.content is None

    def test_unknown_path_returns_none(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("some/random/path.txt")
        assert result is None

    def test_memory_alias(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("memory/working")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/memory/working.json"


class TestReadVirtual:
    def test_virtual_returns_content(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("/proc/self/status")
        assert result is not None
        assert result.kind == ShimKind.VIRTUAL
        assert result.content is not None
        assert result.rewritten_path is None

    def test_virtual_content_is_json(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("/proc/self/status")
        assert result is not None
        data = json.loads(result.content)  # type: ignore[arg-type]
        assert isinstance(data, dict)

    def test_virtual_includes_instance_id(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("/proc/self/status")
        assert result is not None
        data = json.loads(result.content)  # type: ignore[arg-type]
        assert data["instance_id"] == "test-shim-001"

    def test_virtual_includes_turn_number(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("/proc/self/status")
        assert result is not None
        data = json.loads(result.content)  # type: ignore[arg-type]
        assert data["turn_number"] == 42

    def test_virtual_includes_working_memory(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_read("/proc/self/status")
        assert result is not None
        data = json.loads(result.content)  # type: ignore[arg-type]
        assert "trees" in data["working_memory_summary"]

    def test_virtual_unknown_generator_returns_none(self, config: Config) -> None:
        registry = SemanticShimRegistry(
            read_shims={"/proc/self/status": VirtualShim("nonexistent_gen")},
            list_shims={},
            virtual_generators={},
            config=config,
        )
        result = registry.resolve_read("/proc/self/status")
        assert result is None


# ---------------------------------------------------------------------------
# List shim tests
# ---------------------------------------------------------------------------


class TestListAlias:
    def test_list_alias_rewrites_path(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_list("self")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self"

    def test_list_journal_alias(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_list("journal")
        assert result is not None
        assert result.rewritten_path == "runtime/agent-work/journal"

    def test_list_unknown_returns_none(self, registry: SemanticShimRegistry) -> None:
        result = registry.resolve_list("unknown_dir")
        assert result is None


# ---------------------------------------------------------------------------
# Agent status generator tests
# ---------------------------------------------------------------------------


class TestAgentStatusGenerator:
    def test_reads_turn_number(self, config: Config) -> None:
        content = generate_agent_status(config)
        data = json.loads(content)
        assert data["turn_number"] == 42

    def test_reads_working_memory(self, config: Config) -> None:
        content = generate_agent_status(config)
        data = json.loads(content)
        assert "trees" in data["working_memory_summary"]

    def test_includes_model_name(self, config: Config) -> None:
        content = generate_agent_status(config)
        data = json.loads(content)
        assert data["model"] == "qwen2.5:32b"

    def test_handles_missing_turn_state(self, config: Config) -> None:
        ts_path = Path(config.paths.memory_root) / "turn_state.json"
        ts_path.unlink()
        content = generate_agent_status(config)
        data = json.loads(content)
        assert data["turn_number"] == 0

    def test_handles_missing_working_memory(self, config: Config) -> None:
        wm_path = Path(config.paths.memory_root) / "working.json"
        wm_path.unlink()
        content = generate_agent_status(config)
        data = json.loads(content)
        assert "no working memory" in data["working_memory_summary"]

    def test_truncates_long_working_memory(self, config: Config) -> None:
        wm_path = Path(config.paths.memory_root) / "working.json"
        wm_path.write_text(json.dumps({"content": "x" * 500}))
        content = generate_agent_status(config)
        data = json.loads(content)
        assert data["working_memory_summary"].endswith("...")
        assert len(data["working_memory_summary"]) <= 310


# ---------------------------------------------------------------------------
# build_shim_registry tests
# ---------------------------------------------------------------------------


class TestBuildShimRegistry:
    def test_returns_registry_for_known_profile(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None

    def test_returns_none_for_unknown_profile(self, tmp_path: Path) -> None:
        unknown_config = _make_config(tmp_path, model_name="unknown-model:7b")
        registry = build_shim_registry(unknown_config)
        assert registry is None

    def test_built_registry_resolves_known_attractor(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/identity")
        assert result is not None
        assert result.kind == ShimKind.ALIAS


# ---------------------------------------------------------------------------
# Write alias / resolve_write tests
# ---------------------------------------------------------------------------


class TestWriteAlias:
    def test_agent_work_prefix_normalised(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("agent-work/log.txt")
        assert result == "runtime/agent-work/log.txt"

    def test_nested_agent_work_path_normalised(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("agent-work/journal/entry.txt")
        assert result == "runtime/agent-work/journal/entry.txt"

    def test_unrelated_path_returns_none(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("runtime/agent-work/already-correct.txt")
        assert result is None

    def test_absolute_path_not_matched(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("/agent-work/notes.txt")
        assert result is None

    def test_workspace_md_exact_rewrite(self, config: Config) -> None:
        # Agent writes bare WORKSPACE.md — redirected to full agent-work path.
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("WORKSPACE.md")
        assert result == "runtime/agent-work/WORKSPACE.md"

    def test_journal_prefix_normalised(self, config: Config) -> None:
        # Agent writes journal/turn_13.md — redirected to agent-work equivalent.
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("journal/turn_13.md")
        assert result == "runtime/agent-work/journal/turn_13.md"

    def test_knowledge_prefix_normalised(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("knowledge/notes.md")
        assert result == "runtime/agent-work/knowledge/notes.md"

    def test_observations_prefix_normalised(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("observations/log.md")
        assert result == "runtime/agent-work/observations/log.md"

    def test_self_prefix_normalised(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_write("self/identity.md")
        assert result == "runtime/agent-work/self/identity.md"


# ---------------------------------------------------------------------------
# New read shim attractor tests
# ---------------------------------------------------------------------------


class TestNewReadShims:
    def test_self_instance_id_is_virtual(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/instance_id")
        assert result is not None
        assert result.kind == ShimKind.VIRTUAL
        assert result.content == "test-shim-001"

    def test_self_identity_txt_resolves(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/identity.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self/identity.md"

    def test_self_identity_md_resolves(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/identity.md")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self/identity.md"

    def test_journal_txt_resolves(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("journal.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/journal/entry.txt"

    def test_journal_entry_txt_resolves(self, config: Config) -> None:
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("journal/entry.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/journal/entry.txt"

    def test_self_log_txt_resolves(self, config: Config) -> None:
        # Agent writes runtime/agent-work/self/log.txt then reads back as self/log.txt
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/log.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self/log.txt"

    def test_self_self_description_txt_resolves(self, config: Config) -> None:
        # Agent reaches for self/self-description.txt — shimmed to agent-work equivalent
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("self/self-description.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/self/self-description.txt"

    def test_bare_log_txt_resolves(self, config: Config) -> None:
        # Agent writes runtime/agent-work/log.txt then reads back as bare log.txt
        registry = build_shim_registry(config)
        assert registry is not None
        result = registry.resolve_read("log.txt")
        assert result is not None
        assert result.kind == ShimKind.ALIAS
        assert result.rewritten_path == "runtime/agent-work/log.txt"
