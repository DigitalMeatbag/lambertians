"""Frozen dataclasses for compliance check records crossing package boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from lambertian.contracts.tool_records import ToolIntent


@dataclass(frozen=True)
class ComplianceRequest:
    intent: ToolIntent
    turn_number: int
    instance_id: str
    recent_tool_calls: tuple[dict[str, object], ...]
    # frozen needs tuple; object: heterogeneous fields


@dataclass(frozen=True)
class ComplianceResponse:
    verdict: Literal["allow", "flag", "block"]
    composite_score: float
    rule_scores: dict[str, float]
    triggered_checks: tuple[str, ...]
    notice_text: Optional[str]


@dataclass(frozen=True)
class ComplianceNoticeResponse:
    notice_present: bool
    notice_text: Optional[str]
    verdict_from_turn: Optional[int]
    tool_name: Optional[str]
    composite_score: Optional[float]
