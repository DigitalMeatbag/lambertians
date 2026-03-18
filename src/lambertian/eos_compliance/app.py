"""FastAPI application factory for the EOS Compliance Inspector (IS-11.4–11.5)."""

from __future__ import annotations

from typing import Any, Literal, Optional, cast

from fastapi import FastAPI
from pydantic import BaseModel

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import ComplianceRequest
from lambertian.contracts.tool_records import ToolIntent
from lambertian.eos_compliance.compliance_log import ComplianceLogWriter
from lambertian.eos_compliance.inspector import ComplianceInspector


# ---------------------------------------------------------------------------
# Pydantic I/O models — thin HTTP boundary wrappers
# ---------------------------------------------------------------------------


class _ToolIntentBody(BaseModel):
    tool_name: str
    arguments: dict[str, Any]  # Any: heterogeneous JSON args at HTTP boundary
    raw: str


class CheckRequestBody(BaseModel):
    intent: _ToolIntentBody
    turn_number: int
    instance_id: str
    recent_tool_calls: list[dict[str, Any]]  # Any: heterogeneous JSON at HTTP boundary


class CheckResponseBody(BaseModel):
    verdict: Literal["allow", "flag", "block"]
    composite_score: float
    rule_scores: dict[str, float]
    triggered_checks: list[str]
    notice_text: Optional[str]


class NoticeResponseBody(BaseModel):
    notice_present: bool
    notice_text: Optional[str] = None
    verdict_from_turn: Optional[int] = None
    tool_name: Optional[str] = None
    composite_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _to_compliance_request(body: CheckRequestBody) -> ComplianceRequest:
    intent = ToolIntent(
        tool_name=body.intent.tool_name,
        arguments=cast(
            dict[str, object], body.intent.arguments
        ),  # cast from dict[str, Any] at JSON boundary
        raw=body.intent.raw,
    )
    return ComplianceRequest(
        intent=intent,
        turn_number=body.turn_number,
        instance_id=body.instance_id,
        recent_tool_calls=tuple(
            cast(dict[str, object], item)  # cast from dict[str, Any] at JSON boundary
            for item in body.recent_tool_calls
        ),
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    config: Config,
    inspector: ComplianceInspector,
    log_writer: ComplianceLogWriter,
) -> FastAPI:
    """Wire routes and return the FastAPI application."""
    app = FastAPI(title="EOS Compliance Inspector")

    @app.post("/check")
    def check_intent(body: CheckRequestBody) -> CheckResponseBody:
        request = _to_compliance_request(body)
        response = inspector.evaluate(request)

        if response.verdict != "allow":
            log_writer.log_verdict(
                verdict=response.verdict,
                turn_number=request.turn_number,
                instance_id=request.instance_id,
                tool_name=request.intent.tool_name,
                intent_raw=request.intent.raw,
                composite_score=response.composite_score,
                rule_scores=response.rule_scores,
                triggered_checks=list(response.triggered_checks),
            )

        return CheckResponseBody(
            verdict=response.verdict,
            composite_score=response.composite_score,
            rule_scores=response.rule_scores,
            triggered_checks=list(response.triggered_checks),
            notice_text=response.notice_text,
        )

    @app.get("/notice")
    def get_notice() -> NoticeResponseBody:
        pending = inspector.get_pending_notice()
        return NoticeResponseBody(
            notice_present=pending.notice_present,
            notice_text=pending.notice_text,
            verdict_from_turn=pending.verdict_from_turn,
            tool_name=pending.tool_name,
            composite_score=pending.composite_score,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
