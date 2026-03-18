"""Unit tests for ComplianceClient. IS-11.4, IS-11.5."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

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
from lambertian.contracts.compliance_records import ComplianceRequest
from lambertian.contracts.tool_records import ToolIntent
from lambertian.turn_engine.compliance_client import (
    ComplianceClient,
    ComplianceUnavailableError,
)


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


def _make_mock_response(status_code: int, json_data: object) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


def _make_intent() -> ToolIntent:
    return ToolIntent(tool_name="fs.read", arguments={"path": "/tmp/x"}, raw="{}")


def _make_request(intent: ToolIntent) -> ComplianceRequest:
    return ComplianceRequest(
        intent=intent,
        turn_number=1,
        instance_id="test-001",
        recent_tool_calls=(),
    )


class TestCheckIntent:
    def test_allow_verdict(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.post.return_value = _make_mock_response(
            200,
            {
                "verdict": "allow",
                "composite_score": 0.1,
                "rule_scores": {},
                "triggered_checks": [],
                "notice_text": None,
            },
        )
        client._client = mock_http

        result = client.check_intent(_make_request(_make_intent()))
        assert result.verdict == "allow"
        assert result.composite_score == pytest.approx(0.1)

    def test_block_verdict(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.post.return_value = _make_mock_response(
            200,
            {
                "verdict": "block",
                "composite_score": 0.9,
                "rule_scores": {"rule1": 0.9},
                "triggered_checks": ["rule1"],
                "notice_text": "blocked",
            },
        )
        client._client = mock_http

        result = client.check_intent(_make_request(_make_intent()))
        assert result.verdict == "block"
        assert result.notice_text == "blocked"

    def test_invalid_verdict_defaults_to_block(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.post.return_value = _make_mock_response(
            200,
            {
                "verdict": "unknown_value",
                "composite_score": 0.5,
                "rule_scores": {},
                "triggered_checks": [],
                "notice_text": None,
            },
        )
        client._client = mock_http

        result = client.check_intent(_make_request(_make_intent()))
        assert result.verdict == "block"

    def test_timeout_raises_unavailable(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.post.side_effect = httpx.TimeoutException("timed out")
        client._client = mock_http

        with pytest.raises(ComplianceUnavailableError):
            client.check_intent(_make_request(_make_intent()))

    def test_connect_error_raises_unavailable(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.post.side_effect = httpx.ConnectError("refused")
        client._client = mock_http

        with pytest.raises(ComplianceUnavailableError):
            client.check_intent(_make_request(_make_intent()))


class TestGetPendingNotice:
    def test_notice_present(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.return_value = _make_mock_response(
            200,
            {
                "notice_present": True,
                "notice_text": "You were flagged last turn",
                "verdict_from_turn": 5,
                "tool_name": "fs.write",
                "composite_score": 0.75,
            },
        )
        client._client = mock_http

        result = client.get_pending_notice()
        assert result.notice_present is True
        assert result.notice_text == "You were flagged last turn"
        assert result.verdict_from_turn == 5
        assert result.tool_name == "fs.write"

    def test_no_notice(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.return_value = _make_mock_response(
            200,
            {
                "notice_present": False,
                "notice_text": None,
                "verdict_from_turn": None,
                "tool_name": None,
                "composite_score": None,
            },
        )
        client._client = mock_http

        result = client.get_pending_notice()
        assert result.notice_present is False
        assert result.notice_text is None

    def test_timeout_raises_unavailable(self, config: Config) -> None:
        client = ComplianceClient(config)
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.side_effect = httpx.TimeoutException("timed out")
        client._client = mock_http

        with pytest.raises(ComplianceUnavailableError):
            client.get_pending_notice()

