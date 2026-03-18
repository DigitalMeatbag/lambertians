"""Frozen dataclasses for turn context and records crossing package boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from lambertian.contracts.tool_records import ToolCallRecord


@dataclass(frozen=True)
class DriverMessage:
    role: Literal["USER", "SELF_PROMPT"]
    content: str
    source: Literal["external", "self_generated"]


@dataclass
class TurnContext:
    turn_number: int
    instance_id: str
    timestamp_start: str  # ISO 8601 UTC
    constitution_block: str
    self_model_block: str
    eos_block: str
    compliance_block: Optional[str]
    pain_blocks: list[str]
    ground_block: Optional[str]
    memory_working_block: Optional[str]
    memory_episodic_block: Optional[str]
    driver: DriverMessage
    rolling_context: list[dict[str, object]] = field(default_factory=list)
    # prior TurnRecord dicts; object: heterogeneous event fields


@dataclass(frozen=True)
class TurnRecord:
    turn_number: int
    instance_id: str
    timestamp_start: str
    timestamp_end: str
    driver_role: Literal["USER", "SELF_PROMPT"]
    tool_calls: tuple[ToolCallRecord, ...]  # frozen dataclass needs tuple not list
    pain_message_count: int
    memory_writes: int
    adaptation_class: Optional[Literal["free", "reviewed", "forbidden"]]
    noop: bool
    outcome: Literal["TURN_COMPLETE", "TURN_FAILED"]
