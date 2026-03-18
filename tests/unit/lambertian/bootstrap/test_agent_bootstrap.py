"""Unit tests for AgentBootstrap. IS-5.4."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lambertian.bootstrap.agent_bootstrap import AgentBootstrap
from lambertian.configuration.universe_config import (
    ComplianceConfig,
    Config,
    CreatorObservabilityConfig,
    EosConfig,
    EventStreamConfig,
    FitnessConfig,
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
from lambertian.memory_store.querier import NoOpMemoryQuerier


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "event_stream").mkdir()
    return Config(
        universe=UniverseConfig(
            phase="phase1",
            instance_count=1,
            instance_id="test-001",
            max_age_turns=500,
            startup_grace_seconds=15,
            normal_shutdown_grace_seconds=5,
        ),
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
        ),
        paths=PathsConfig(
            runtime_root=str(tmp_path / "runtime"),
            event_stream_file=str(tmp_path / "runtime" / "event_stream" / "events.jsonl"),
            memory_root=str(tmp_path / "runtime" / "memory"),
            pain_root=str(tmp_path / "runtime" / "pain"),
            graveyard_root=str(tmp_path / "runtime" / "graveyard"),
            fitness_file=str(tmp_path / "runtime" / "fitness" / "current.json"),
            self_model_file=str(tmp_path / "runtime" / "self" / "self_model.json"),
        ),
        creator_observability=CreatorObservabilityConfig(
            live_reviewed_adaptations=True,
            live_compliance_blocks=True,
            live_running_fitness=True,
            read_graveyard_artifacts=True,
        ),
    )


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    p = tmp_path / "universe.toml"
    p.write_text("[universe]\nphase = 'phase1'\n", encoding="utf-8")
    return p


class TestAgentBootstrapConstruction:
    def test_constructs_without_error(
        self, config: Config, config_path: Path
    ) -> None:
        bootstrap = AgentBootstrap(config, config_path)
        assert bootstrap is not None


class TestStartupEvent:
    def test_startup_event_written(
        self, config: Config, config_path: Path
    ) -> None:
        bootstrap = AgentBootstrap(config, config_path)

        written_events: list[tuple[str, int, str, dict[str, object]]] = []

        def capture_write(
            event_type: str,
            turn_number: int,
            source: str,
            extra: dict[str, object],
        ) -> None:
            written_events.append((event_type, turn_number, source, extra))

        bootstrap._event_log.write_event = capture_write  # type: ignore[method-assign]

        # Patch run on the TurnEngine so bootstrap.run() doesn't actually loop
        with patch.object(
            bootstrap,
            "_build_turn_engine",
            return_value=MagicMock(**{"run.return_value": None}),
        ):
            with patch.object(bootstrap._self_model_writer, "write"):
                bootstrap.run()

        startup_events = [e for e in written_events if e[0] == "STARTUP"]
        assert len(startup_events) == 1
        _, turn_num, source, extra = startup_events[0]
        assert turn_num == 0
        assert source == "agent"
        assert "config_hash" in extra
        assert "model_name" in extra
        assert extra["instance_generation"] == 1


class TestMemoryQuerier:
    def test_noop_querier_when_chroma_unavailable(
        self, config: Config, config_path: Path
    ) -> None:
        bootstrap = AgentBootstrap(config, config_path)
        # Chroma is definitely unavailable in test environment
        querier = bootstrap._connect_memory()
        assert isinstance(querier, NoOpMemoryQuerier)

    def test_noop_querier_returns_empty_list(
        self, config: Config, config_path: Path
    ) -> None:
        bootstrap = AgentBootstrap(config, config_path)
        querier = bootstrap._connect_memory()
        assert querier.query_episodic("test", 5) == []

    def test_build_turn_engine_succeeds(
        self, config: Config, config_path: Path
    ) -> None:
        bootstrap = AgentBootstrap(config, config_path)
        engine = bootstrap._build_turn_engine(NoOpMemoryQuerier())
        assert engine is not None
