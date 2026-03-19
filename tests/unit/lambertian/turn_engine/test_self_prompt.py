"""Unit tests for SelfPromptGenerator. IS-6.3 step 7."""

from __future__ import annotations

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
from lambertian.turn_engine.self_prompt import SelfPromptGenerator


@pytest.fixture()
def config() -> Config:
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


@pytest.fixture()
def generator(config: Config) -> SelfPromptGenerator:
    return SelfPromptGenerator(config)


class TestGenerateProducesString:
    def test_returns_string(self, generator: SelfPromptGenerator) -> None:
        result = generator.generate(None, [], [], 1)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_recent_self_prompts_always_novel(
        self, generator: SelfPromptGenerator
    ) -> None:
        result = generator.generate("some context", [], [], 5)
        assert isinstance(result, str)


class TestSimilarity:
    def test_identical_strings_max_similarity(self, generator: SelfPromptGenerator) -> None:
        s = "hello world test"
        sim = generator._similarity(s, s)
        assert sim == pytest.approx(1.0)

    def test_empty_strings_zero(self, generator: SelfPromptGenerator) -> None:
        assert generator._similarity("", "") == 0.0
        assert generator._similarity("abc", "") == 0.0
        assert generator._similarity("", "abc") == 0.0

    def test_very_different_strings_low_similarity(
        self, generator: SelfPromptGenerator
    ) -> None:
        sim = generator._similarity(
            "quantum physics neutron stars",
            "apple banana cooking recipe",
        )
        assert sim < 0.3

    def test_short_strings_under_trigram_length(
        self, generator: SelfPromptGenerator
    ) -> None:
        # Strings shorter than 3 chars produce no trigrams → similarity 0
        assert generator._similarity("ab", "ab") == 0.0


class TestIsNovel:
    def test_similar_prompt_rejected(self, generator: SelfPromptGenerator) -> None:
        existing = [{"text": "What is the current state of my environment?", "turn": 1}]
        candidate = "What is the current state of my environment?"
        assert generator._is_novel(candidate, existing) is False

    def test_dissimilar_prompt_accepted(self, generator: SelfPromptGenerator) -> None:
        existing = [{"text": "quantum mechanics and particle physics", "turn": 1}]
        candidate = "What is cooking and food preparation?"
        assert generator._is_novel(candidate, existing) is True

    def test_empty_recent_always_novel(self, generator: SelfPromptGenerator) -> None:
        assert generator._is_novel("anything at all", []) is True


class TestGenerateFallback:
    def test_fallback_contains_turn_number_when_all_similar(
        self, generator: SelfPromptGenerator
    ) -> None:
        # Patch _is_novel to always return False so retries are exhausted
        with patch.object(generator, "_is_novel", return_value=False):
            result = generator.generate(None, [], [], turn_number=42)
        assert "42" in result

