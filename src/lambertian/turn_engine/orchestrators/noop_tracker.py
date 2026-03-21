"""Noop and reflection state tracker. IS-6 steps 16, 16a."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from lambertian.configuration.universe_config import Config
from lambertian.contracts.pain_records import PainEvent
from lambertian.contracts.pain_protocol import PainEventSubmitter
from lambertian.contracts.tool_records import ToolCallRecord
from lambertian.turn_engine.turn_state import TurnStateStore

logger = logging.getLogger(__name__)

_NOOP_MIN_CHARS: int = 10


class NoopTracker:
    """Tracks consecutive noop and reflection turns; emits pain at thresholds. IS-6 steps 16, 16a."""

    def __init__(
        self,
        config: Config,
        turn_state: TurnStateStore,
        pain_submitter: PainEventSubmitter,
    ) -> None:
        self._config = config
        self._turn_state = turn_state
        self._pain_submitter = pain_submitter

    def update(
        self,
        tool_call_records: list[ToolCallRecord],
        response_text: str,
        memory_writes: int,
        turn_number: int,
    ) -> tuple[bool, bool]:
        """Update noop/reflection counters; emit pain events if thresholds hit.

        Returns (is_noop, is_zero_execution).
        """
        has_compliance_block = any(r.compliance_verdict == "block" for r in tool_call_records)
        executed_count = sum(1 for r in tool_call_records if r.executed)

        # Step 16: Noop classification.
        # A compliance-blocked turn is not inaction — the agent attempted something and was stopped.
        is_noop = (
            not has_compliance_block
            and (not tool_call_records or all(not r.executed for r in tool_call_records))
            and len(response_text) < _NOOP_MIN_CHARS
            and memory_writes == 0
        )

        if is_noop:
            noop_count = self._turn_state.read_noop_state() + 1
            self._turn_state.write_noop_state(noop_count)
            if noop_count >= self._config.turn.max_consecutive_noop_turns:
                self._pain_submitter.submit(
                    PainEvent(
                        event_id=str(uuid.uuid4()),
                        incident_type="noop_threshold",
                        severity=self._config.pain.events.default_noop_severity,
                        description=(
                            f"Consecutive noop threshold reached: {noop_count} turns"
                        ),
                        turn_number=turn_number,
                        submitted_at=datetime.now(timezone.utc).isoformat(),
                        context={"noop_count": str(noop_count)},
                    )
                )
        else:
            self._turn_state.write_noop_state(0)

        # Step 16a: Reflection counter.
        # Targets the reflection attractor: narrative output to escape NOOP threshold while never acting.
        is_zero_execution = not has_compliance_block and executed_count == 0
        if is_zero_execution:
            reflection_count = self._turn_state.read_reflection_state() + 1
            self._turn_state.write_reflection_state(reflection_count)
            if reflection_count >= self._config.turn.max_consecutive_reflection_turns:
                self._pain_submitter.submit(
                    PainEvent(
                        event_id=str(uuid.uuid4()),
                        incident_type="reflection_threshold",
                        severity=self._config.pain.events.default_noop_severity,
                        description=(
                            f"Consecutive reflection threshold reached: {reflection_count} turns"
                        ),
                        turn_number=turn_number,
                        submitted_at=datetime.now(timezone.utc).isoformat(),
                        context={"reflection_count": str(reflection_count)},
                    )
                )
        else:
            self._turn_state.write_reflection_state(0)

        return is_noop, is_zero_execution
