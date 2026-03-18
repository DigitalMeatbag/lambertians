"""Unit tests for PromptBlockAssembler and SelfModelWriter. IS-4.2, IS-4.4, IS-4.5a."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lambertian.configuration.universe_config import (
    ComplianceConfig,
    Config,
    CreatorObservabilityConfig,
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
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.self_model.self_model_writer import SelfModelWriter


@pytest.fixture()
def config() -> Config:
    return Config(
        universe=UniverseConfig(
            phase="phase1",
            instance_count=1,
            instance_id="test-instance-001",
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
    )


@pytest.fixture()
def assembler(config: Config) -> PromptBlockAssembler:
    return PromptBlockAssembler(config)


class TestConstitutionBlock:
    def test_starts_with_tag(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.constitution_block()
        assert block.startswith("[SYSTEM_CONSTITUTION]")

    def test_contains_four_rules(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.constitution_block()
        assert "Ya gotta eat" in block
        assert "Don't be a dick" in block
        assert "Don't be a lump" in block
        assert "Do nothing on purpose" in block

    def test_is_deterministic(self, assembler: PromptBlockAssembler) -> None:
        assert assembler.constitution_block() == assembler.constitution_block()


class TestSelfModelBlock:
    def test_starts_with_tag(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.self_model_block()
        assert block.startswith("[SYSTEM_SELF_MODEL]")

    def test_contains_instance_id(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.self_model_block()
        assert "test-instance-001" in block

    def test_is_valid_json(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.self_model_block()
        # Strip the tag line and the blank line that follows it.
        lines = block.split("\n", 2)
        json_str = lines[2] if len(lines) > 2 else lines[-1]
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_json_structure(self, assembler: PromptBlockAssembler, config: Config) -> None:
        block = assembler.self_model_block()
        lines = block.split("\n", 2)
        data = json.loads(lines[2])
        assert data["instance_id"] == config.universe.instance_id
        assert data["max_age_turns"] == config.universe.max_age_turns
        assert data["model_name"] == config.model.name
        assert data["is_alive"] is True
        assert data["eos"]["label"] == config.eos.label
        assert data["eos"]["rules"][0] == config.eos.rule_1

    def test_known_conditions_present(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.self_model_block()
        lines = block.split("\n", 2)
        data = json.loads(lines[2])
        kc = data["known_conditions"]
        assert kc["pain_channel_present"] is True
        assert kc["mortality_present"] is True
        assert kc["compliance_inspector_present"] is True


class TestEosBlock:
    def test_starts_with_tag(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.eos_block()
        assert block.startswith("[SYSTEM_EOS]")

    def test_contains_admissibility_section(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.eos_block()
        assert "ADMISSIBILITY" in block

    def test_contains_scope_model(self, assembler: PromptBlockAssembler) -> None:
        block = assembler.eos_block()
        assert "SCOPE MODEL" in block

    def test_is_deterministic(self, assembler: PromptBlockAssembler) -> None:
        assert assembler.eos_block() == assembler.eos_block()


class TestSelfModelWriter:
    def test_write_creates_file(self, config: Config, tmp_path: Path) -> None:
        writer = SelfModelWriter(config, tmp_path / "self")
        writer.write()
        target = tmp_path / "self" / "self_model.json"
        assert target.exists()

    def test_write_produces_valid_json(self, config: Config, tmp_path: Path) -> None:
        writer = SelfModelWriter(config, tmp_path / "self")
        writer.write()
        target = tmp_path / "self" / "self_model.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["instance_id"] == config.universe.instance_id

    def test_write_creates_parent_dir(self, config: Config, tmp_path: Path) -> None:
        deep_dir = tmp_path / "a" / "b" / "self"
        writer = SelfModelWriter(config, deep_dir)
        writer.write()
        assert (deep_dir / "self_model.json").exists()

    def test_write_no_system_tag_in_file(self, config: Config, tmp_path: Path) -> None:
        writer = SelfModelWriter(config, tmp_path / "self")
        writer.write()
        raw = (tmp_path / "self" / "self_model.json").read_text(encoding="utf-8")
        assert "[SYSTEM_SELF_MODEL]" not in raw

