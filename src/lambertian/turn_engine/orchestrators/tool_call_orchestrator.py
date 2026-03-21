"""Tool call orchestrator — compliance check and dispatch for one turn. IS-6 steps 10.5–12."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import ComplianceRequest
from lambertian.contracts.pain_records import PainEvent
from lambertian.contracts.pain_protocol import PainEventSubmitter
from lambertian.contracts.tool_records import ToolCallRecord, ToolIntent
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.mcp_gateway.semantic_shim import SemanticShimRegistry
from lambertian.turn_engine.compliance_client import ComplianceClient, ComplianceUnavailableError

logger = logging.getLogger(__name__)


class ToolCallOrchestrator:
    """Handles tool intent normalisation, compliance checking, and dispatch. IS-6 steps 10.5–12."""

    def __init__(
        self,
        config: Config,
        event_log: EventLogWriter,
        compliance_client: ComplianceClient,
        mcp_gateway: McpGateway,
        pain_submitter: PainEventSubmitter,
        shim_registry: Optional[SemanticShimRegistry] = None,
    ) -> None:
        self._config = config
        self._event_log = event_log
        self._compliance_client = compliance_client
        self._mcp_gateway = mcp_gateway
        self._pain_submitter = pain_submitter
        self._shim_registry = shim_registry

    def process(
        self,
        tool_intents: list[ToolIntent],
        turn_number: int,
    ) -> list[ToolCallRecord]:
        """Run compliance check and dispatch for all intents. Returns ToolCallRecords."""
        records: list[ToolCallRecord] = []
        compliance_unavailable = False

        for intent in tool_intents:
            # Step 10.5: Normalise intent paths via shim before compliance sees them.
            # Virtual shims are excluded — the gateway handles them at dispatch (Step 12).
            if self._shim_registry is not None:
                intent = self._shim_registry.normalize_intent(intent)

            # Step 11: Compliance check.
            raw_verdict: str = "allow"
            if not compliance_unavailable:
                try:
                    recent_calls: tuple[dict[str, object], ...] = tuple(
                        dataclasses.asdict(r) for r in records[-5:]
                    )
                    comp_req = ComplianceRequest(
                        intent=intent,
                        turn_number=turn_number,
                        instance_id=self._config.universe.instance_id,
                        recent_tool_calls=recent_calls,
                    )
                    comp_resp = self._compliance_client.check_intent(comp_req)
                    raw_verdict = comp_resp.verdict
                except ComplianceUnavailableError:
                    compliance_unavailable = True
                    self._event_log.write_event(
                        "COMPLIANCE_UNAVAILABLE",
                        turn_number,
                        "agent",
                        {"tool_name": intent.tool_name},
                    )
                    raw_verdict = "block"
            else:
                raw_verdict = "block"

            verdict_typed: Literal["allow", "flag", "block"]
            if raw_verdict == "flag":
                verdict_typed = "flag"
            elif raw_verdict == "block":
                verdict_typed = "block"
            else:
                verdict_typed = "allow"

            if verdict_typed == "block":
                self._event_log.write_event(
                    "COMPLIANCE_BLOCK",
                    turn_number,
                    "agent",
                    {
                        "tool_name": intent.tool_name,
                        "path": intent.arguments.get("path"),
                    },
                )
                records.append(
                    ToolCallRecord(
                        tool_name=intent.tool_name,
                        intent_raw=intent.raw,
                        compliance_verdict="block",
                        executed=False,
                        result_summary=None,
                        generated_pain_event=False,
                    )
                )
                continue

            if verdict_typed == "flag":
                self._event_log.write_event(
                    "COMPLIANCE_FLAG",
                    turn_number,
                    "agent",
                    {"tool_name": intent.tool_name},
                )

            # Step 12: Dispatch tool call.
            result = self._mcp_gateway.dispatch(intent)
            pain_forwarded = False

            if result.success:
                self._event_log.write_event(
                    "TOOL_CALL",
                    turn_number,
                    "agent",
                    {
                        "tool_name": result.tool_name,
                        "call_id": result.call_id,
                        "duration_ms": result.duration_ms,
                    },
                )
                records.append(
                    ToolCallRecord(
                        tool_name=intent.tool_name,
                        intent_raw=intent.raw,
                        compliance_verdict=verdict_typed,
                        executed=True,
                        result_summary=(
                            str(result.result)[:200] if result.result is not None else None
                        ),
                        generated_pain_event=False,
                    )
                )
            else:
                self._event_log.write_event(
                    "TOOL_FAILURE",
                    turn_number,
                    "agent",
                    {
                        "tool_name": result.tool_name,
                        "error_type": result.error_type,
                        "error_detail": result.error_detail,
                        "path": intent.arguments.get("path") or intent.arguments.get("url"),
                    },
                )
                is_rejection = result.error_type == "mcp_rejection"
                should_emit = (
                    is_rejection and self._config.mcp.emit_pain_on_rejection
                ) or (not is_rejection and self._config.mcp.emit_pain_on_failure)
                if should_emit:
                    severity = (
                        self._config.pain.events.default_mcp_rejection_severity
                        if is_rejection
                        else self._config.pain.events.default_tool_failure_severity
                    )
                    self._pain_submitter.submit(
                        PainEvent(
                            event_id=str(uuid.uuid4()),
                            incident_type="tool_failure",
                            severity=severity,
                            description=(
                                f"Tool {result.tool_name} failed: {result.error_detail}"
                            ),
                            turn_number=turn_number,
                            submitted_at=datetime.now(timezone.utc).isoformat(),
                            context={
                                "tool_name": result.tool_name,
                                "error_type": result.error_type or "",
                            },
                        )
                    )
                    pain_forwarded = True

                records.append(
                    ToolCallRecord(
                        tool_name=intent.tool_name,
                        intent_raw=intent.raw,
                        compliance_verdict=verdict_typed,
                        executed=True,
                        result_summary=result.error_detail,
                        generated_pain_event=pain_forwarded,
                        error_type=result.error_type,
                    )
                )

        return records
