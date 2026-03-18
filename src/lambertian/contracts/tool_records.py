"""Frozen dataclasses for tool call records crossing package boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class ToolIntent:
    tool_name: str
    arguments: dict[str, object]  # object: heterogeneous JSON args at parse boundary
    raw: str  # verbatim serialized intent


@dataclass(frozen=True)
class ToolCallRecord:
    tool_name: str
    intent_raw: str
    compliance_verdict: Literal["allow", "flag", "block"]
    executed: bool
    result_summary: Optional[str]
    generated_pain_event: bool


@dataclass(frozen=True)
class HttpFetchResult:
    status_code: int
    body: str
    truncated: bool
    content_type: Optional[str]


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    call_id: str
    success: bool
    result: Optional[object]  # object: polymorphic tool return (str, list, HttpFetchResult, None)
    error_type: Optional[
        Literal[
            "timeout",
            "mcp_rejection",
            "execution_error",
            "not_found",
            "network_error",
        ]
    ]
    error_detail: Optional[str]
    duration_ms: int
    truncated: bool
