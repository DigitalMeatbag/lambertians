"""Append-only compliance log writer (IS-11.6)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


class ComplianceLogWriter:
    """Appends flag/block verdict records to a JSONL file (IS-11.6).

    Append mode is used throughout — the file grows but is never atomically replaced.
    Parent directory is created on first write.
    """

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path

    def log_verdict(
        self,
        verdict: Literal["flag", "block"],
        turn_number: int,
        instance_id: str,
        tool_name: str,
        intent_raw: str,
        composite_score: float,
        rule_scores: dict[str, float],
        triggered_checks: list[str],
    ) -> None:
        """Append one JSONL record. Creates parent directory if needed."""
        record: dict[str, Any] = {  # Any: heterogeneous JSON record at file-write boundary
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_number": turn_number,
            "instance_id": instance_id,
            "verdict": verdict,
            "tool_name": tool_name,
            "intent_raw": intent_raw,
            "composite_score": composite_score,
            "rule_scores": rule_scores,
            "triggered_checks": triggered_checks,
        }
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
