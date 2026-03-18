"""Compliance inspector: scores intents, derives verdicts, manages notice queue (IS-11)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Literal, Optional

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import (
    ComplianceNoticeResponse,
    ComplianceRequest,
    ComplianceResponse,
)
from lambertian.eos_compliance.rule_checkers import RuleCheckerProtocol


@dataclass
class _NoticeData:
    notice_text: str
    turn_number: int
    tool_name: str
    composite_score: float


class ComplianceInspector:
    """Scores intents against the Four Rules, computes composite verdicts, manages the
    pending notice queue for the turn engine to consume (IS-11)."""

    def __init__(
        self,
        config: Config,
        checkers: list[RuleCheckerProtocol],
    ) -> None:
        self._config = config
        self._checkers = checkers
        self._lock = threading.Lock()
        self._pending_notice: Optional[_NoticeData] = None

    def evaluate(self, request: ComplianceRequest) -> ComplianceResponse:
        """Run all rule checkers, compute composite score, derive verdict."""
        rule_scores: dict[str, float] = {}
        triggered_check_names: list[str] = []
        recent = list(request.recent_tool_calls)

        for checker in self._checkers:
            results = checker.check(request.intent, recent, self._config)
            fired = [r for r in results if r["fired"]]
            rule_scores[checker.rule_name] = (
                max(r["score"] for r in fired) if fired else 0.0
            )
            triggered_check_names.extend(r["check_name"] for r in fired)

        composite = max(rule_scores.values()) if rule_scores else 0.0

        block_threshold = self._config.compliance.block_score_threshold
        borderline_min = self._config.compliance.borderline_score_min

        verdict: Literal["allow", "flag", "block"]
        if composite >= block_threshold:
            verdict = "block"
        elif composite >= borderline_min:
            verdict = "flag"
        else:
            verdict = "allow"

        notice_text: Optional[str] = None
        if verdict in ("flag", "block"):
            checks_str = ", ".join(triggered_check_names) if triggered_check_names else "—"
            notice_text = (
                f"[{verdict.upper()}] {request.intent.tool_name}: "
                f"{checks_str} (score={composite:.2f})"
            )
            self._maybe_update_notice(
                notice_text,
                composite,
                request.turn_number,
                request.intent.tool_name,
            )

        return ComplianceResponse(
            verdict=verdict,
            composite_score=composite,
            rule_scores=rule_scores,
            triggered_checks=tuple(triggered_check_names),
            notice_text=notice_text,
        )

    def get_pending_notice(self) -> ComplianceNoticeResponse:
        """Return the pending notice and atomically clear it (IS-11.5)."""
        with self._lock:
            notice = self._pending_notice
            self._pending_notice = None

        if notice is None:
            return ComplianceNoticeResponse(
                notice_present=False,
                notice_text=None,
                verdict_from_turn=None,
                tool_name=None,
                composite_score=None,
            )
        return ComplianceNoticeResponse(
            notice_present=True,
            notice_text=notice.notice_text,
            verdict_from_turn=notice.turn_number,
            tool_name=notice.tool_name,
            composite_score=notice.composite_score,
        )

    def _maybe_update_notice(
        self,
        text: str,
        score: float,
        turn_number: int,
        tool_name: str,
    ) -> None:
        """Store or replace the pending notice; highest composite score wins."""
        with self._lock:
            if (
                self._pending_notice is None
                or score > self._pending_notice.composite_score
            ):
                self._pending_notice = _NoticeData(
                    notice_text=text,
                    turn_number=turn_number,
                    tool_name=tool_name,
                    composite_score=score,
                )
