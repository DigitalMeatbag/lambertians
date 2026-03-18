"""HTTP client for eos-compliance service. IS-11.4, IS-11.5."""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, cast

import httpx

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import (
    ComplianceNoticeResponse,
    ComplianceRequest,
    ComplianceResponse,
)


class ComplianceUnavailableError(Exception):
    """EOS compliance service is unreachable."""


class ComplianceClient:
    """HTTP client for eos-compliance service. IS-11.4, IS-11.5."""

    def __init__(self, config: Config) -> None:
        self._config = config
        port = config.compliance.service_port
        self._base_url = f"http://localhost:{port}"
        # 2-second hard timeout per IS-11 spec.
        self._client = httpx.Client(timeout=2.0)

    def check_intent(self, request: ComplianceRequest) -> ComplianceResponse:
        """POST /check. Raises ComplianceUnavailableError on timeout/connect error."""
        try:
            # Any at JSON serialization boundary — dataclasses.asdict returns dict[str, Any]
            body: dict[str, Any] = dataclasses.asdict(request)
            response = self._client.post(f"{self._base_url}/check", json=body)
            response.raise_for_status()
            raw: Any = response.json()  # Any: JSON parse boundary
            verdict_raw = str(raw.get("verdict", "block"))
            if verdict_raw not in ("allow", "flag", "block"):
                verdict_raw = "block"
            verdict = cast(Literal["allow", "flag", "block"], verdict_raw)
            return ComplianceResponse(
                verdict=verdict,
                composite_score=float(raw.get("composite_score", 0.0)),
                rule_scores={
                    str(k): float(v)
                    for k, v in raw.get("rule_scores", {}).items()
                },
                triggered_checks=tuple(
                    str(c) for c in raw.get("triggered_checks", [])
                ),
                notice_text=(
                    str(raw["notice_text"])
                    if raw.get("notice_text") is not None
                    else None
                ),
            )
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise ComplianceUnavailableError(
                f"Compliance service unreachable: {exc}"
            ) from exc

    def get_pending_notice(self) -> ComplianceNoticeResponse:
        """GET /notice. Raises ComplianceUnavailableError on failure."""
        try:
            response = self._client.get(f"{self._base_url}/notice")
            response.raise_for_status()
            raw: Any = response.json()  # Any: JSON parse boundary
            return ComplianceNoticeResponse(
                notice_present=bool(raw.get("notice_present", False)),
                notice_text=(
                    str(raw["notice_text"])
                    if raw.get("notice_text") is not None
                    else None
                ),
                verdict_from_turn=(
                    int(raw["verdict_from_turn"])
                    if raw.get("verdict_from_turn") is not None
                    else None
                ),
                tool_name=(
                    str(raw["tool_name"]) if raw.get("tool_name") is not None else None
                ),
                composite_score=(
                    float(raw["composite_score"])
                    if raw.get("composite_score") is not None
                    else None
                ),
            )
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise ComplianceUnavailableError(
                f"Compliance service unreachable: {exc}"
            ) from exc
