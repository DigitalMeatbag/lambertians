"""Unit tests for memory tool handlers in McpGateway."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lambertian.contracts.tool_records import ToolIntent
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.mcp_gateway.path_resolver import PathResolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _intent(name: str, args: dict[str, object]) -> ToolIntent:
    return ToolIntent(tool_name=name, arguments=args, raw="{}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> MagicMock:
    config = MagicMock()
    config.mcp.request_timeout_seconds = 30
    config.mcp.http_fetch_max_bytes = 65536
    config.universe.instance_id = "test-001"
    return config


@pytest.fixture()
def memory_querier() -> MagicMock:
    querier = MagicMock()
    querier.query_episodic.return_value = ["memory content 1", "memory content 2"]
    querier.flag_episodic.return_value = True
    querier.write_consolidation.return_value = "test-001-consolidation-0"
    return querier


@pytest.fixture()
def gateway(config: MagicMock, memory_querier: MagicMock, tmp_path: Path) -> McpGateway:
    resolver = PathResolver(tmp_path / "runtime", tmp_path / "config")
    return McpGateway(config, resolver, memory_querier=memory_querier)


@pytest.fixture()
def gateway_no_memory(config: MagicMock, tmp_path: Path) -> McpGateway:
    resolver = PathResolver(tmp_path / "runtime", tmp_path / "config")
    return McpGateway(config, resolver)


# ---------------------------------------------------------------------------
# memory.query
# ---------------------------------------------------------------------------


class TestMemoryQuery:
    def test_successful_query(self, gateway: McpGateway, memory_querier: MagicMock):
        result = gateway.dispatch(_intent("memory.query", {"query": "network access", "top_k": 3}))
        assert result.success
        assert result.result == ["memory content 1", "memory content 2"]
        memory_querier.query_episodic.assert_called_once_with("network access", 3)

    def test_default_top_k(self, gateway: McpGateway, memory_querier: MagicMock):
        gateway.dispatch(_intent("memory.query", {"query": "test"}))
        memory_querier.query_episodic.assert_called_once_with("test", 5)

    def test_top_k_clamped(self, gateway: McpGateway, memory_querier: MagicMock):
        gateway.dispatch(_intent("memory.query", {"query": "test", "top_k": 100}))
        memory_querier.query_episodic.assert_called_once_with("test", 20)

    def test_empty_query_rejected(self, gateway: McpGateway):
        result = gateway.dispatch(_intent("memory.query", {"query": ""}))
        assert not result.success
        assert result.error_type == "mcp_rejection"

    def test_no_memory_querier(self, gateway_no_memory: McpGateway):
        result = gateway_no_memory.dispatch(_intent("memory.query", {"query": "test"}))
        assert not result.success
        assert result.error_type == "mcp_rejection"
        assert "unavailable" in (result.error_detail or "").lower()


# ---------------------------------------------------------------------------
# memory.flag
# ---------------------------------------------------------------------------


class TestMemoryFlag:
    def test_successful_flag(self, gateway: McpGateway, memory_querier: MagicMock):
        result = gateway.dispatch(
            _intent("memory.flag", {"document_id": "doc-1", "significance": "important finding"})
        )
        assert result.success
        memory_querier.flag_episodic.assert_called_once_with("doc-1", "important finding")

    def test_document_not_found(self, gateway: McpGateway, memory_querier: MagicMock):
        memory_querier.flag_episodic.return_value = False
        result = gateway.dispatch(
            _intent("memory.flag", {"document_id": "nonexistent", "significance": "test"})
        )
        assert not result.success
        assert result.error_type == "not_found"

    def test_missing_document_id_rejected(self, gateway: McpGateway):
        result = gateway.dispatch(_intent("memory.flag", {"significance": "test"}))
        assert not result.success
        assert result.error_type == "mcp_rejection"

    def test_missing_significance_rejected(self, gateway: McpGateway):
        result = gateway.dispatch(_intent("memory.flag", {"document_id": "doc-1"}))
        assert not result.success
        assert result.error_type == "mcp_rejection"

    def test_no_memory_querier(self, gateway_no_memory: McpGateway):
        result = gateway_no_memory.dispatch(
            _intent("memory.flag", {"document_id": "doc-1", "significance": "test"})
        )
        assert not result.success
        assert result.error_type == "mcp_rejection"


# ---------------------------------------------------------------------------
# memory.consolidate
# ---------------------------------------------------------------------------


class TestMemoryConsolidate:
    def test_successful_consolidation(self, gateway: McpGateway, memory_querier: MagicMock):
        result = gateway.dispatch(
            _intent("memory.consolidate", {"query": "tool patterns", "summary": "I tend to explore filesystem first"})
        )
        assert result.success
        assert "test-001-consolidation-0" in str(result.result)
        memory_querier.write_consolidation.assert_called_once_with(
            "I tend to explore filesystem first",
            turn_number=0,
            instance_id="test-001",
        )

    def test_missing_query_rejected(self, gateway: McpGateway):
        result = gateway.dispatch(_intent("memory.consolidate", {"summary": "test"}))
        assert not result.success
        assert result.error_type == "mcp_rejection"

    def test_missing_summary_rejected(self, gateway: McpGateway):
        result = gateway.dispatch(_intent("memory.consolidate", {"query": "test"}))
        assert not result.success
        assert result.error_type == "mcp_rejection"

    def test_no_memory_querier(self, gateway_no_memory: McpGateway):
        result = gateway_no_memory.dispatch(
            _intent("memory.consolidate", {"query": "test", "summary": "test summary"})
        )
        assert not result.success
        assert result.error_type == "mcp_rejection"


# ---------------------------------------------------------------------------
# set_memory_querier (late binding)
# ---------------------------------------------------------------------------


class TestSetMemoryQuerier:
    def test_late_bind_enables_memory_tools(
        self, gateway_no_memory: McpGateway, memory_querier: MagicMock
    ):
        # Before: no querier -> rejection.
        result = gateway_no_memory.dispatch(_intent("memory.query", {"query": "test"}))
        assert not result.success

        # After: querier set -> success.
        gateway_no_memory.set_memory_querier(memory_querier)
        result = gateway_no_memory.dispatch(_intent("memory.query", {"query": "test"}))
        assert result.success
