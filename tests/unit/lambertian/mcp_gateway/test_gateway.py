"""Unit tests for McpGateway dispatch. IS-7."""

from __future__ import annotations

from pathlib import Path
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
from lambertian.contracts.tool_records import HttpFetchResult, ToolIntent
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.mcp_gateway.path_resolver import PathResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
            max_consecutive_reflection_turns=5,
        ),
        mcp=McpConfig(
            request_timeout_seconds=30,
            retry_count=0,
            emit_pain_on_failure=True,
            emit_pain_on_rejection=True,
            http_fetch_max_bytes=100,  # small limit to test truncation easily
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
        policy=PolicyConfig(
            response_excerpt_max_chars=500,
            tool_result_summary_max_chars=150,
            working_memory_excerpt_max_chars=400,
            suppression_threshold=3,
            repetition_detection_window=3,
            rolling_context_extraction_count=5,
        ),
    )


@pytest.fixture()
def runtime_base(tmp_path: Path) -> Path:
    p = tmp_path / "runtime"
    p.mkdir()
    return p


@pytest.fixture()
def config_base(tmp_path: Path) -> Path:
    p = tmp_path / "config"
    p.mkdir()
    return p


@pytest.fixture()
def resolver(runtime_base: Path, config_base: Path) -> PathResolver:
    return PathResolver(runtime_base, config_base)


@pytest.fixture()
def gateway(config: Config, resolver: PathResolver) -> McpGateway:
    return McpGateway(config, resolver)


def make_intent(tool_name: str, arguments: dict[str, Any]) -> ToolIntent:
    return ToolIntent(tool_name=tool_name, arguments=arguments, raw="{}")


# ---------------------------------------------------------------------------
# fs.read
# ---------------------------------------------------------------------------


class TestFsRead:
    def test_success(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "memory" / "file.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("hello world", encoding="utf-8")

        result = gateway.dispatch(make_intent("fs.read", {"path": str(target)}))
        assert result.success is True
        assert result.result == "hello world"
        assert result.error_type is None

    def test_not_found(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "memory" / "nonexistent.txt"
        result = gateway.dispatch(make_intent("fs.read", {"path": str(target)}))
        assert result.success is False
        assert result.error_type == "not_found"

    def test_boundary_violation(self, gateway: McpGateway, tmp_path: Path) -> None:
        outside = tmp_path / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        result = gateway.dispatch(make_intent("fs.read", {"path": str(outside)}))
        assert result.success is False
        assert result.error_type == "mcp_rejection"

    def test_has_call_id(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "memory" / "file.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
        result = gateway.dispatch(make_intent("fs.read", {"path": str(target)}))
        assert result.call_id != ""


# ---------------------------------------------------------------------------
# fs.write
# ---------------------------------------------------------------------------


class TestFsWrite:
    def test_overwrite_creates_file(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "agent-work" / "output.txt"
        result = gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "hello"})
        )
        assert result.success is True
        assert target.read_text(encoding="utf-8") == "hello"

    def test_overwrite_replaces_content(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "agent-work" / "output.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("old", encoding="utf-8")
        gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "new", "mode": "overwrite"})
        )
        assert target.read_text(encoding="utf-8") == "new"

    def test_append_adds_content(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "agent-work" / "log.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("line1\n", encoding="utf-8")
        gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "line2\n", "mode": "append"})
        )
        assert target.read_text(encoding="utf-8") == "line1\nline2\n"

    def test_boundary_violation_memory(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "memory" / "poisoned.db"
        result = gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "bad"})
        )
        assert result.success is False
        assert result.error_type == "mcp_rejection"

    def test_boundary_violation_outside(self, gateway: McpGateway, tmp_path: Path) -> None:
        target = tmp_path / "outside.txt"
        result = gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "bad"})
        )
        assert result.success is False
        assert result.error_type == "mcp_rejection"

    def test_creates_parent_dirs(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "agent-work" / "deep" / "nested" / "file.txt"
        result = gateway.dispatch(
            make_intent("fs.write", {"path": str(target), "content": "deep"})
        )
        assert result.success is True
        assert target.read_text(encoding="utf-8") == "deep"


# ---------------------------------------------------------------------------
# fs.list
# ---------------------------------------------------------------------------


class TestFsList:
    def test_success(self, gateway: McpGateway, runtime_base: Path) -> None:
        mem_dir = runtime_base / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "a.txt").write_text("a")
        (mem_dir / "b.txt").write_text("b")

        result = gateway.dispatch(make_intent("fs.list", {"path": str(mem_dir)}))
        assert result.success is True
        assert isinstance(result.result, list)
        names = set(result.result)
        assert "a.txt" in names
        assert "b.txt" in names

    def test_not_found(self, gateway: McpGateway, runtime_base: Path) -> None:
        target = runtime_base / "memory" / "nonexistent_dir"
        result = gateway.dispatch(make_intent("fs.list", {"path": str(target)}))
        assert result.success is False
        assert result.error_type == "not_found"

    def test_boundary_violation(self, gateway: McpGateway, tmp_path: Path) -> None:
        result = gateway.dispatch(make_intent("fs.list", {"path": str(tmp_path / "hidden")}))
        assert result.success is False
        assert result.error_type == "mcp_rejection"


# ---------------------------------------------------------------------------
# http.fetch
# ---------------------------------------------------------------------------


class TestHttpFetch:
    def _make_mock_response(
        self, status_code: int = 200, text: str = "body", content_type: str = "text/plain"
    ) -> MagicMock:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text
        response.headers = httpx.Headers({"content-type": content_type})
        return response

    def test_success(self, config: Config, resolver: PathResolver) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._make_mock_response(200, "hello")
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com"}))
        assert result.success is True
        assert isinstance(result.result, HttpFetchResult)
        assert result.result.status_code == 200
        assert result.result.body == "hello"
        assert result.result.truncated is False

    def test_truncation(self, config: Config, resolver: PathResolver) -> None:
        # config.mcp.http_fetch_max_bytes = 100
        long_body = "x" * 200
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._make_mock_response(200, long_body)
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com"}))
        assert result.success is True
        assert isinstance(result.result, HttpFetchResult)
        assert result.result.truncated is True
        assert len(result.result.body) == 100
        assert result.truncated is True

    def test_http_404_is_success(self, config: Config, resolver: PathResolver) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._make_mock_response(404, "not found")
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com/missing"}))
        assert result.success is True
        assert isinstance(result.result, HttpFetchResult)
        assert result.result.status_code == 404

    def test_http_500_is_success(self, config: Config, resolver: PathResolver) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._make_mock_response(500, "server error")
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com"}))
        assert result.success is True

    def test_timeout(self, config: Config, resolver: PathResolver) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com"}))
        assert result.success is False
        assert result.error_type == "timeout"

    def test_network_error(self, config: Config, resolver: PathResolver) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.ConnectError("connection refused")
        gw = McpGateway(config, resolver, http_client=mock_client)

        result = gw.dispatch(make_intent("http.fetch", {"url": "http://example.com"}))
        assert result.success is False
        assert result.error_type == "network_error"

    def test_non_get_rejected(self, config: Config, resolver: PathResolver) -> None:
        gw = McpGateway(config, resolver)
        result = gw.dispatch(
            make_intent("http.fetch", {"url": "http://example.com", "method": "POST"})
        )
        assert result.success is False
        assert result.error_type == "mcp_rejection"

    def test_default_user_agent_sent(self, config: Config, resolver: PathResolver) -> None:
        """Gateway sets a default User-Agent on all http.fetch requests."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_response.headers = httpx.Headers({"content-type": "text/plain"})

        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.get.return_value = mock_response

        with patch("lambertian.mcp_gateway.gateway.httpx.Client", return_value=mock_instance) as mock_cls:
            gw = McpGateway(config, resolver)  # no injected client
            gw.dispatch(make_intent("http.fetch", {"url": "https://example.com"}))

            headers = mock_cls.call_args.kwargs.get("headers", {})
            assert "User-Agent" in headers
            assert "lambertian" in headers["User-Agent"].lower()


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------


class TestUnknownTool:
    def test_unknown_tool_mcp_rejection(self, gateway: McpGateway) -> None:
        result = gateway.dispatch(make_intent("fs.delete", {}))
        assert result.success is False
        assert result.error_type == "mcp_rejection"
        assert "fs.delete" in (result.error_detail or "")

    def test_unknown_tool_has_tool_name(self, gateway: McpGateway) -> None:
        result = gateway.dispatch(make_intent("nonexistent.tool", {}))
        assert result.tool_name == "nonexistent.tool"

