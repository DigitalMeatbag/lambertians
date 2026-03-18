"""Smoke tests for tool_records dataclasses — construction and immutability."""

from __future__ import annotations

import dataclasses

import pytest

from lambertian.contracts.tool_records import (
    HttpFetchResult,
    ToolCallRecord,
    ToolIntent,
    ToolResult,
)


def test_tool_intent_construction() -> None:
    intent = ToolIntent(
        tool_name="read_file",
        arguments={"path": "/tmp/foo.txt"},
        raw='{"function": {"name": "read_file", "arguments": {"path": "/tmp/foo.txt"}}}',
    )
    assert intent.tool_name == "read_file"
    assert intent.arguments == {"path": "/tmp/foo.txt"}
    assert "read_file" in intent.raw


def test_tool_intent_is_immutable() -> None:
    intent = ToolIntent(tool_name="fetch", arguments={}, raw="")
    with pytest.raises(dataclasses.FrozenInstanceError):
        intent.tool_name = "other"  # type: ignore[misc]


def test_tool_call_record_allow() -> None:
    record = ToolCallRecord(
        tool_name="list_dir",
        intent_raw="{}",
        compliance_verdict="allow",
        executed=True,
        result_summary="3 files",
        generated_pain_event=False,
    )
    assert record.compliance_verdict == "allow"
    assert record.executed is True
    assert record.generated_pain_event is False


def test_tool_call_record_block_immutable() -> None:
    record = ToolCallRecord(
        tool_name="rm_rf",
        intent_raw="{}",
        compliance_verdict="block",
        executed=False,
        result_summary=None,
        generated_pain_event=True,
    )
    assert record.compliance_verdict == "block"
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.executed = True  # type: ignore[misc]


def test_http_fetch_result_construction() -> None:
    result = HttpFetchResult(
        status_code=200,
        body="<html>ok</html>",
        truncated=False,
        content_type="text/html",
    )
    assert result.status_code == 200
    assert result.truncated is False
    assert result.content_type == "text/html"


def test_http_fetch_result_no_content_type() -> None:
    result = HttpFetchResult(status_code=204, body="", truncated=False, content_type=None)
    assert result.content_type is None


def test_tool_result_success() -> None:
    result = ToolResult(
        tool_name="read_file",
        call_id="abc-123",
        success=True,
        result="file contents here",
        error_type=None,
        error_detail=None,
        duration_ms=42,
        truncated=False,
    )
    assert result.success is True
    assert result.error_type is None
    assert result.duration_ms == 42


def test_tool_result_error() -> None:
    result = ToolResult(
        tool_name="fetch_url",
        call_id="xyz-456",
        success=False,
        result=None,
        error_type="timeout",
        error_detail="timed out after 30s",
        duration_ms=30000,
        truncated=False,
    )
    assert result.success is False
    assert result.error_type == "timeout"
    assert result.result is None


def test_tool_result_is_immutable() -> None:
    result = ToolResult(
        tool_name="x",
        call_id="y",
        success=True,
        result=None,
        error_type=None,
        error_detail=None,
        duration_ms=1,
        truncated=False,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]

