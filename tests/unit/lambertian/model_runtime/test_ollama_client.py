"""Unit tests for OllamaClient — mock httpx, no network."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
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
from lambertian.contracts.tool_records import ToolIntent
from lambertian.model_runtime.ollama_client import OllamaClient, OllamaInferenceError


@pytest.fixture()
def config() -> Config:
    return Config(
        universe=UniverseConfig(
            phase="phase1",
            instance_count=1,
            instance_id="test-001",
            max_age_turns=1000,
            startup_grace_seconds=5,
            normal_shutdown_grace_seconds=5,
        ),
        model=ModelConfig(
            provider="ollama",
            name="phi4",
            endpoint_url="http://localhost:11434",
            request_timeout_seconds=30,
            context_window_tokens=8192,
            max_output_tokens=2048,
            temperature=0.6,
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
    )


def _make_mock_response(body: dict[str, Any], status_code: int = 200) -> MagicMock:
    mock = MagicMock(spec=httpx.Response)
    mock.is_success = status_code < 400
    mock.status_code = status_code
    mock.text = json.dumps(body)
    mock.json.return_value = body
    return mock


def test_chat_success_no_tool_calls(config: Config) -> None:
    client = OllamaClient(config)
    body: dict[str, Any] = {
        "message": {"role": "assistant", "content": "Hello, world!", "tool_calls": []}
    }
    with patch.object(client._client, "post", return_value=_make_mock_response(body)):
        text, intents = client.chat(
            [{"role": "user", "content": "hi"}], []
        )
    assert text == "Hello, world!"
    assert intents == []


def test_chat_success_with_tool_calls(config: Config) -> None:
    client = OllamaClient(config)
    body: dict[str, Any] = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "/tmp/foo.txt"},
                    }
                },
                {
                    "function": {
                        "name": "list_dir",
                        "arguments": {"dir": "/tmp"},
                    }
                },
            ],
        }
    }
    with patch.object(client._client, "post", return_value=_make_mock_response(body)):
        text, intents = client.chat(
            [{"role": "user", "content": "list files"}], []
        )
    assert text == ""
    assert len(intents) == 2
    assert intents[0].tool_name == "read_file"
    assert intents[0].arguments == {"path": "/tmp/foo.txt"}
    assert "read_file" in intents[0].raw
    assert intents[1].tool_name == "list_dir"


def test_chat_tool_call_raw_is_valid_json(config: Config) -> None:
    client = OllamaClient(config)
    tc: dict[str, Any] = {"function": {"name": "ping", "arguments": {}}}
    body: dict[str, Any] = {
        "message": {"role": "assistant", "content": "", "tool_calls": [tc]}
    }
    with patch.object(client._client, "post", return_value=_make_mock_response(body)):
        _, intents = client.chat([], [])
    parsed: Any = json.loads(intents[0].raw)
    assert parsed["function"]["name"] == "ping"


def test_chat_timeout_raises_inference_error(config: Config) -> None:
    client = OllamaClient(config)
    with patch.object(
        client._client, "post", side_effect=httpx.TimeoutException("timed out")
    ):
        with pytest.raises(OllamaInferenceError, match="timeout"):
            client.chat([], [])


def test_chat_connect_error_raises_inference_error(config: Config) -> None:
    client = OllamaClient(config)
    with patch.object(
        client._client, "post", side_effect=httpx.ConnectError("refused")
    ):
        with pytest.raises(OllamaInferenceError, match="Connection error"):
            client.chat([], [])


def test_chat_http_error_returns_error_text(config: Config) -> None:
    client = OllamaClient(config)
    mock = MagicMock(spec=httpx.Response)
    mock.is_success = False
    mock.status_code = 503
    mock.text = "Service Unavailable"
    with patch.object(client._client, "post", return_value=mock):
        text, intents = client.chat([], [])
    assert "503" in text
    assert intents == []


def test_embed_success(config: Config) -> None:
    client = OllamaClient(config)
    embedding = [0.1, 0.2, 0.3, 0.4]
    body: dict[str, Any] = {"embeddings": [embedding]}
    mock = _make_mock_response(body)
    mock.raise_for_status = MagicMock()
    with patch.object(client._client, "post", return_value=mock):
        result = client.embed("hello world")
    assert result == pytest.approx([0.1, 0.2, 0.3, 0.4])


def test_embed_timeout_raises_inference_error(config: Config) -> None:
    client = OllamaClient(config)
    with patch.object(
        client._client, "post", side_effect=httpx.TimeoutException("timeout")
    ):
        with pytest.raises(OllamaInferenceError, match="timeout"):
            client.embed("test")

