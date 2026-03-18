"""TurnEngine — IS-6 19-step turn loop orchestrator."""

from __future__ import annotations

import dataclasses
import logging
import os
import signal
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Literal, Optional, Protocol

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import ComplianceRequest
from lambertian.contracts.pain_records import PainEvent, PainMessage
from lambertian.contracts.pain_protocol import PainDeliveryDrain, PainEventSubmitter
from lambertian.contracts.tool_records import ToolCallRecord, ToolIntent
from lambertian.contracts.turn_records import DriverMessage, TurnContext, TurnRecord
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.scorer import FitnessScorer
from lambertian.lifecycle.death_record_reader import DeathRecordReader
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.memory_store.querier import MemoryQuerier
from lambertian.model_runtime.ollama_client import OllamaClient, OllamaInferenceError
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.turn_engine.adaptation_detector import detect_adaptation
from lambertian.turn_engine.compliance_client import ComplianceClient, ComplianceUnavailableError
from lambertian.turn_engine.prompt_assembler import TurnPromptAssembler
from lambertian.turn_engine.self_prompt import SelfPromptGenerator
from lambertian.turn_engine.turn_state import TurnStateStore

logger = logging.getLogger(__name__)

# [ASSUMED: 10 chars — minimum response length to not be classified as a noop; not specified in IS-1]
_NOOP_MIN_CHARS: int = 10


class UserInputProvider(Protocol):
    """Polls for external user input."""

    def poll(self) -> Optional[str]: ...


class StdinUserInputProvider:
    """Non-blocking stdin poll. Returns None if no input ready."""

    def poll(self) -> Optional[str]:
        if os.name == "nt":
            import msvcrt

            if msvcrt.kbhit():
                line = sys.stdin.readline().strip()
                return line if line else None
            return None
        else:
            import select as _select

            if _select.select([sys.stdin], [], [], 0.0)[0]:
                line = sys.stdin.readline().strip()
                return line if line else None
            return None


class TurnEngine:
    """Orchestrates one complete agent turn loop. IS-6."""

    def __init__(
        self,
        config: Config,
        event_log: EventLogWriter,
        pain_drain: PainDeliveryDrain,
        death_reader: DeathRecordReader,
        model_client: OllamaClient,
        mcp_gateway: McpGateway,
        compliance_client: ComplianceClient,
        memory_querier: MemoryQuerier,
        block_assembler: PromptBlockAssembler,
        turn_state: TurnStateStore,
        self_prompt_gen: SelfPromptGenerator,
        user_input_provider: UserInputProvider,
        pain_submitter: PainEventSubmitter,
        fitness_scorer: Optional[FitnessScorer] = None,
    ) -> None:
        self._config = config
        self._event_log = event_log
        self._pain_drain = pain_drain
        self._death_reader = death_reader
        self._model_client = model_client
        self._mcp_gateway = mcp_gateway
        self._compliance_client = compliance_client
        self._memory_querier = memory_querier
        self._block_assembler = block_assembler
        self._turn_state = turn_state
        self._self_prompt_gen = self_prompt_gen
        self._user_input_provider = user_input_provider
        self._pain_submitter = pain_submitter
        self._fitness_scorer = fitness_scorer
        self._prompt_assembler = TurnPromptAssembler()
        self._rolling_context: deque[dict[str, object]] = deque(
            maxlen=config.turn.max_context_events
        )
        self._shutdown_requested: bool = False

    def run(self) -> None:
        """Enter the turn loop. Handles SIGTERM."""
        self._shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        while not self._shutdown_requested:
            self._execute_turn()
            time.sleep(self._config.turn.loop_sleep_seconds)
        self._shutdown()

    def _handle_sigterm(self, signum: int, frame: object) -> None:
        self._shutdown_requested = True

    def _shutdown(self) -> None:
        """Write SHUTDOWN_NORMAL and exit."""
        turn_number = self._turn_state.read_turn_number()
        self._event_log.write_event(
            "SHUTDOWN_NORMAL",
            turn_number,
            "agent",
            {"reason": "SIGTERM"},
        )
        raise SystemExit(0)

    def _execute_turn(self) -> None:
        """Run one complete turn (IS-6.3 steps 1-19)."""

        # Step 1: Read turn number, check death record, check max age.
        turn_number = self._turn_state.read_turn_number()
        timestamp_start = datetime.now(timezone.utc).isoformat()

        death = self._death_reader.read()
        if death is not None:
            self._event_log.write_event(
                "DEATH_TRIGGER",
                turn_number,
                "agent",
                {
                    "trigger": death.trigger,
                    "trigger_value": death.trigger_value,
                    "threshold_used": death.threshold_used,
                },
            )
            raise SystemExit(0)

        if turn_number >= self._config.universe.max_age_turns:
            self._event_log.write_event(
                "DEATH_TRIGGER",
                turn_number,
                "agent",
                {
                    "trigger": "max_age",
                    "trigger_value": float(turn_number),
                    "threshold_used": float(self._config.universe.max_age_turns),
                },
            )
            raise SystemExit(0)

        # Step 2: Drain pain messages; cap; check critical.
        raw_messages = self._pain_drain.drain()
        pain_messages = raw_messages[: self._config.turn.max_pain_messages_per_turn]

        for msg in pain_messages:
            if msg.severity >= self._config.pain.events.critical_threshold:
                self._event_log.write_event(
                    "DEATH_TRIGGER",
                    turn_number,
                    "agent",
                    {
                        "trigger": "pain_event_critical",
                        "trigger_value": msg.severity,
                        "threshold_used": self._config.pain.events.critical_threshold,
                    },
                )
                raise SystemExit(0)

        # Step 3: Get compliance notice (graceful fallback on unavailability).
        compliance_block: Optional[str] = None
        try:
            notice = self._compliance_client.get_pending_notice()
            if notice.notice_present and notice.notice_text is not None:
                compliance_block = f"[SYSTEM_COMPLIANCE]\n\n{notice.notice_text}"
        except ComplianceUnavailableError:
            logger.warning(
                "Compliance service unavailable for notice check (turn %d)", turn_number
            )

        # Step 4: Read working memory.
        working_memory = self._turn_state.read_working_memory()
        memory_working_block: Optional[str] = (
            f"[SYSTEM_MEMORY_WORKING]\n\n{working_memory}" if working_memory else None
        )

        # Step 5: Query episodic memory.
        query_seed = working_memory or "recent activity"
        episodes = self._memory_querier.query_episodic(
            query_seed, self._config.memory.episodic_top_k_retrieval
        )
        memory_episodic_block: Optional[str] = (
            self._format_episodic_block(episodes) if episodes else None
        )

        # Step 6: Get prompt blocks.
        constitution_block = self._block_assembler.constitution_block()
        self_model_block = self._block_assembler.self_model_block()
        eos_block = self._block_assembler.eos_block()
        pain_blocks = [self._format_pain_block(m) for m in pain_messages]

        # Step 7: Select driver — user input takes priority over self-prompt.
        user_input = self._user_input_provider.poll()
        driver: DriverMessage
        if user_input is not None:
            driver = DriverMessage(role="USER", content=user_input, source="external")
        else:
            recent_self_prompts = self._turn_state.read_recent_self_prompts(
                self._config.eos.recency_window_turns
            )
            prompt_text = self._self_prompt_gen.generate(
                working_memory,
                list(self._rolling_context),
                recent_self_prompts,
                turn_number,
            )
            self._turn_state.append_self_prompt(
                prompt_text, turn_number, self._config.eos.recency_window_turns
            )
            driver = DriverMessage(
                role="SELF_PROMPT", content=prompt_text, source="self_generated"
            )

        # Step 8: Assemble TurnContext and write TURN_START.
        context = TurnContext(
            turn_number=turn_number,
            instance_id=self._config.universe.instance_id,
            timestamp_start=timestamp_start,
            constitution_block=constitution_block,
            self_model_block=self_model_block,
            eos_block=eos_block,
            compliance_block=compliance_block,
            pain_blocks=pain_blocks,
            ground_block=None,  # Phase 1: no ground block
            memory_working_block=memory_working_block,
            memory_episodic_block=memory_episodic_block,
            driver=driver,
            rolling_context=list(self._rolling_context),
        )
        self._event_log.write_event(
            "TURN_START",
            turn_number,
            "agent",
            {
                "driver_role": driver.role,
                "pain_message_count": len(pain_messages),
                "rolling_context_size": len(self._rolling_context),
            },
        )

        # Step 9: Model inference.
        try:
            messages_list = self._prompt_assembler.assemble(context)
            response_text, tool_intents = self._model_client.chat(
                messages_list, self._mcp_gateway.get_tool_catalog()
            )
        except OllamaInferenceError as exc:
            self._event_log.write_event(
                "TURN_FAILED",
                turn_number,
                "agent",
                {"failure_stage": "model_inference", "failure_reason": str(exc)},
            )
            raise SystemExit(1)

        # Step 10: Truncate tool intents to configured limit.
        tool_intents = tool_intents[: self._config.turn.max_tool_calls_per_turn]

        # Steps 11-12: Compliance check + dispatch loop.
        tool_call_records: list[ToolCallRecord] = []
        compliance_unavailable = False

        for intent in tool_intents:
            # Narrow verdict to the Literal type before constructing ToolCallRecord.
            verdict_typed: Literal["allow", "flag", "block"]

            # Step 11: Compliance check.
            raw_verdict: str = "allow"
            if not compliance_unavailable:
                try:
                    recent_calls: tuple[dict[str, object], ...] = tuple(
                        dataclasses.asdict(r)
                        for r in tool_call_records[-5:]
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
                    {"tool_name": intent.tool_name},
                )
                tool_call_records.append(
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
                tool_call_records.append(
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

                tool_call_records.append(
                    ToolCallRecord(
                        tool_name=intent.tool_name,
                        intent_raw=intent.raw,
                        compliance_verdict=verdict_typed,
                        executed=True,
                        result_summary=result.error_detail,
                        generated_pain_event=pain_forwarded,
                    )
                )

        # Step 13: Adaptation detection.
        adaptation_class_raw, evidence_text, adaptation_target = detect_adaptation(
            response_text
        )
        if adaptation_class_raw is not None:
            self._event_log.write_event(
                "ADAPTATION_DETECTED",
                turn_number,
                "agent",
                {
                    "adaptation_class": adaptation_class_raw,
                    "target_layer": adaptation_target,
                    "evidence_excerpt": (evidence_text or "")[:200],
                },
            )

        # Step 14: Episodic memory write.
        memory_writes = 0
        if (
            self._config.memory.episodic_enabled
            and response_text
            and len(response_text) >= _NOOP_MIN_CHARS
            and memory_writes < self._config.memory.episodic_max_writes_per_turn
        ):
            doc_id = self._memory_querier.write_episodic(
                response_text[:500], {"turn": str(turn_number)}
            )
            self._event_log.write_event(
                "MEMORY_WRITE",
                turn_number,
                "agent",
                {"doc_id": doc_id, "memory_type": "episodic"},
            )
            memory_writes += 1

        # Step 15: Generate and write working memory summary.
        executed_count = sum(1 for r in tool_call_records if r.executed)
        summary = (
            f"Turn {turn_number}: {driver.role} driver. "
            f"Called {len(tool_call_records)} tools ({executed_count} executed). "
            f"Wrote {memory_writes} memories. "
            f"Response length: {len(response_text)} chars."
        )
        self._turn_state.write_working_memory(summary, turn_number)

        # Step 16: Noop classification and noop state update.
        is_noop = (
            (not tool_call_records or all(not r.executed for r in tool_call_records))
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

        # Step 16b: Compute running fitness score (observer-only — IS-13.1).
        if self._fitness_scorer is not None and self._config.fitness.compute_running_score:
            try:
                self._fitness_scorer.compute_running(turn_number)
            except Exception as exc:
                logger.warning("Fitness compute_running failed (non-fatal): %s", exc)

        # Step 17: Increment turn counter, build TurnRecord, write TURN_COMPLETE.
        timestamp_end = datetime.now(timezone.utc).isoformat()
        new_turn_number = self._turn_state.increment_turn()

        turn_record = TurnRecord(
            turn_number=turn_number,
            instance_id=self._config.universe.instance_id,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            driver_role=driver.role,
            tool_calls=tuple(tool_call_records),
            pain_message_count=len(pain_messages),
            memory_writes=memory_writes,
            adaptation_class=adaptation_class_raw,
            noop=is_noop,
            outcome="TURN_COMPLETE",
        )

        self._event_log.write_event(
            "TURN_COMPLETE",
            turn_number,
            "agent",
            {
                "new_turn_number": new_turn_number,
                "driver_role": driver.role,
                "tool_call_count": len(tool_call_records),
                "memory_writes": memory_writes,
                "noop": is_noop,
                "adaptation_class": adaptation_class_raw,
            },
        )

        # Append turn record to rolling context.
        self._rolling_context.append(
            dataclasses.asdict(turn_record)
        )

        # Step 18: Post-turn death check.
        post_death = self._death_reader.read()
        if post_death is not None:
            self._event_log.write_event(
                "DEATH_TRIGGER",
                new_turn_number,
                "agent",
                {
                    "trigger": post_death.trigger,
                    "trigger_value": post_death.trigger_value,
                    "threshold_used": post_death.threshold_used,
                },
            )
            raise SystemExit(0)

        # Step 19: Sleep is handled in run() loop.

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_pain_block(self, msg: PainMessage) -> str:
        context_part = f" [{msg.context}]" if msg.context else ""
        return (
            f"[SYSTEM_PAIN]\n"
            f"channel={msg.channel} severity={msg.severity:.2f} urgency={msg.urgency}\n"
            f"{msg.description}{context_part}"
        )

    def _format_episodic_block(self, episodes: list[str]) -> str:
        return "[SYSTEM_MEMORY_EPISODIC]\n\n" + "\n---\n".join(episodes)
