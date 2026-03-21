"""TurnEngine — IS-6 19-step turn loop orchestrator."""

from __future__ import annotations

import dataclasses
import logging
import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Protocol

from lambertian.configuration.universe_config import Config
from lambertian.contracts.pain_records import PainMessage
from lambertian.contracts.pain_protocol import PainDeliveryDrain, PainEventSubmitter
from lambertian.contracts.tool_records import ToolIntent
from lambertian.contracts.turn_records import DriverMessage, TurnContext, TurnRecord
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.scorer import FitnessScorer
from lambertian.lifecycle.death_record_reader import DeathRecordReader
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.mcp_gateway.semantic_shim import SemanticShimRegistry
from lambertian.pain_monitor.death_guard import DeathGuard
from lambertian.memory_store.querier import MemoryQuerier
from lambertian.memory_store.retrieval_result import MemoryWriteRequest
from lambertian.model_runtime.ollama_client import OllamaClient, OllamaInferenceError
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.turn_engine.adaptation_detector import detect_adaptation
from lambertian.turn_engine.compliance_client import ComplianceClient, ComplianceUnavailableError
from lambertian.turn_engine.orchestrators.noop_tracker import NoopTracker
from lambertian.turn_engine.orchestrators.tool_call_orchestrator import ToolCallOrchestrator
from lambertian.turn_engine.prompt_assembler import TurnPromptAssembler
from lambertian.turn_engine.self_prompt import SelfPromptGenerator
from lambertian.turn_engine.suppression import get_suppressed_tools
from lambertian.turn_engine.turn_state import TurnStateStore

logger = logging.getLogger(__name__)

# [ASSUMED: 10 chars — minimum response length to not be classified as a noop; not specified in IS-1]
_NOOP_MIN_CHARS: int = 10


def _format_intent(intent: ToolIntent) -> str:
    """Compact human-readable representation of a tool call for log output."""
    args = intent.arguments
    name = intent.tool_name
    if name in ("fs.list", "fs.read"):
        return f"{name}({args.get('path', '?')!r})"
    if name == "fs.write":
        content = args.get("content", "")
        size = len(str(content)) if content else 0
        return f"{name}({args.get('path', '?')!r}, {size}chars)"
    if name == "http.fetch":
        url = str(args.get("url", "?"))
        display = url if len(url) <= 80 else url[:77] + "..."
        return f"{name}({display!r})"
    # Generic fallback: show first argument value if present.
    if args:
        first_val = next(iter(args.values()))
        return f"{name}({first_val!r})"
    return name


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
        death_guard: DeathGuard,
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
        shim_registry: Optional[SemanticShimRegistry] = None,
    ) -> None:
        self._config = config
        self._event_log = event_log
        self._pain_drain = pain_drain
        self._death_reader = death_reader
        self._death_guard = death_guard
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
        self._shim_registry = shim_registry
        self._prompt_assembler = TurnPromptAssembler()
        self._rolling_context: deque[dict[str, object]] = deque(
            maxlen=config.turn.max_context_events
        )
        self._shutdown_requested: bool = False
        self._tool_call_orchestrator = ToolCallOrchestrator(
            config=config,
            event_log=event_log,
            compliance_client=compliance_client,
            mcp_gateway=mcp_gateway,
            pain_submitter=pain_submitter,
            shim_registry=shim_registry,
        )
        self._noop_tracker = NoopTracker(
            config=config,
            turn_state=turn_state,
            pain_submitter=pain_submitter,
        )

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
            ground_block=self._build_ground_block(turn_number),
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
        # Suppress tools called exclusively for the last N turns to break repetition loops.
        # NOOP turns are transparent to the suppression window (see suppression.py).
        suppressed_tools = get_suppressed_tools(list(self._rolling_context))
        full_catalog = self._mcp_gateway.get_tool_catalog()
        if suppressed_tools:
            filtered_catalog = [
                t for t in full_catalog
                if not (
                    isinstance(t.get("function"), dict)
                    and t["function"].get("name") in suppressed_tools
                )
            ]
            active_catalog = filtered_catalog if filtered_catalog else full_catalog
            logger.info(
                "[t%d] tool suppression active — suppressed: %s",
                turn_number,
                ", ".join(suppressed_tools),
            )
        else:
            active_catalog = full_catalog
        try:
            messages_list = self._prompt_assembler.assemble(context)
            response_text, tool_intents = self._model_client.chat(
                messages_list, active_catalog
            )
        except OllamaInferenceError as exc:
            self._event_log.write_event(
                "TURN_FAILED",
                turn_number,
                "agent",
                {"failure_stage": "model_inference", "failure_reason": str(exc)},
            )
            self._death_guard.write_death_record(
                trigger="turn_failed",
                trigger_value=0.0,
                threshold_used=0.0,
                turn_number=turn_number,
            )
            raise SystemExit(1)

        logger.info(
            "[t%d][%s] %s%s",
            turn_number,
            driver.role,
            response_text or "(no text — tool call only)",
            (
                "  →tools: " + ", ".join(_format_intent(i) for i in tool_intents)
                if tool_intents
                else ""
            ),
        )

        # Step 10: Truncate tool intents to configured limit.
        tool_intents = tool_intents[: self._config.turn.max_tool_calls_per_turn]

        # Steps 10.5–12: Compliance check + dispatch loop (delegated to ToolCallOrchestrator).
        tool_call_records = self._tool_call_orchestrator.process(tool_intents, turn_number)

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
        # When response_text is empty (silent tool calls), synthesize a structured
        # summary from tool results so episodic memory receives meaningful content.
        # All paths go through the worthiness checker to block repetitive writes.
        memory_writes = 0
        if self._config.memory.episodic_enabled:
            # Determine what content and document type to write.
            write_content: str = ""
            doc_type: str = "model_response"
            if response_text and len(response_text) >= _NOOP_MIN_CHARS:
                write_content = response_text[:500]
                doc_type = "model_response"
            elif tool_call_records:
                # Silent-call model path: synthesize a compact turn summary.
                parts: list[str] = []
                for r in tool_call_records:
                    if r.executed and r.result_summary:
                        parts.append(f"{r.tool_name}: {r.result_summary[:150]}")
                    elif r.executed:
                        parts.append(f"{r.tool_name}: (executed)")
                if parts:
                    write_content = f"[t{turn_number}] " + " | ".join(parts)
                    doc_type = "tool_result"

            if (
                write_content
                and len(write_content) >= _NOOP_MIN_CHARS
                and memory_writes < self._config.memory.episodic_max_writes_per_turn
            ):
                request = MemoryWriteRequest(
                    content=write_content,
                    document_type=doc_type,
                    turn_number=turn_number,
                    write_index=memory_writes,
                    tool_name=None,
                    adaptation_class=None,
                )
                doc_id = self._memory_querier.write_episodic_worthy(
                    request, self._config.universe.instance_id
                )
                if doc_id:
                    self._event_log.write_event(
                        "MEMORY_WRITE",
                        turn_number,
                        "agent",
                        {"doc_id": doc_id, "memory_type": "episodic", "doc_type": doc_type},
                    )
                    memory_writes += 1

        # Step 15: Generate and write working memory summary.
        # Working memory is the primary feed for self-prompt topic extraction.
        # Response content leads so _extract_topic (split on ".") gets real content,
        # not the mechanical header.  Metadata follows on its own line.
        executed_count = sum(1 for r in tool_call_records if r.executed)
        tool_summary = f"tools:{executed_count}/{len(tool_call_records)} mem:{memory_writes}"
        response_excerpt = response_text.strip()[:400] if response_text else ""
        summary = f"{response_excerpt}\n[t{turn_number} {driver.role} {tool_summary}]"
        self._turn_state.write_working_memory(summary, turn_number)

        # Steps 16–16a: Noop/reflection classification and counter update (delegated to NoopTracker).
        is_noop, _ = self._noop_tracker.update(
            tool_call_records, response_text, memory_writes, turn_number
        )

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

    def _build_ground_block(self, turn_number: int) -> Optional[str]:
        """Assemble [SYSTEM_GROUND] per IS-7.7.

        Turn 1: inject full tool catalog with names, signatures, and descriptions.
        Any turn after a turn with mcp_rejection or compliance-blocked calls:
            inject rejection/block reasons verbatim with tool name and argument.
        Returns None when neither condition applies.
        """
        parts: list[str] = []

        if turn_number == 1:
            lines = ["Your available tools (Phase 1 catalog):"]
            for entry in self._mcp_gateway.get_tool_catalog():
                fn = entry.get("function", {})
                if isinstance(fn, dict):
                    name = fn.get("name", "?")
                    desc = fn.get("description", "")
                    props = (fn.get("parameters") or {}).get("properties") or {}
                    sig_parts = []
                    for param, meta in props.items():
                        if isinstance(meta, dict):
                            sig_parts.append(f"{param}: {meta.get('type', 'any')}")
                    sig = f"({', '.join(sig_parts)})"
                    lines.append(f"  {name}{sig} — {desc}")
            lines.append("")
            lines.append("Writable surface: runtime/agent-work/ (fs.write, fs.read, fs.list)")
            lines.append(
                "Read-only surfaces: runtime/memory/, runtime/event_stream/, "
                "runtime/fitness/, runtime/self/, runtime/pain/, runtime/env/, config/"
            )
            lines.append(
                "Paths are relative — no leading slash. "
                "Start with fs.list(\"runtime/\") to discover what's available. "
                "Example read: fs.read(\"runtime/env/host_state.json\")."
            )
            lines.append(
                "runtime/env/host_state.json — live host telemetry, updated every 10s. "
                "Contains CPU load per core, memory pressure, GPU stats, and what's playing "
                "on the speakers right now. Call fs.read(\"runtime/env/host_state.json\") directly."
            )
            parts.append("\n".join(lines))

        if self._rolling_context:
            last = self._rolling_context[-1]
            rejections: list[str] = []
            tool_calls = last.get("tool_calls", [])
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    error_type = tc.get("error_type")
                    verdict = tc.get("compliance_verdict", "")
                    tool_name = tc.get("tool_name", "?")
                    detail = tc.get("result_summary") or ""
                    if error_type == "mcp_rejection":
                        rejections.append(
                            f"  mcp_rejection — {tool_name}: {detail}"
                        )
                    elif verdict == "block" and not tc.get("executed"):
                        rejections.append(
                            f"  compliance_block — {tool_name}: blocked by EOS inspector"
                        )
            if rejections:
                parts.append(
                    "Ground resistance from prior turn:\n" + "\n".join(rejections)
                )

        if not parts:
            return None
        return "[SYSTEM_GROUND]\n\n" + "\n\n".join(parts)

    def _format_pain_block(self, msg: PainMessage) -> str:
        context_part = f" [{msg.context}]" if msg.context else ""
        return (
            f"[SYSTEM_PAIN]\n"
            f"channel={msg.channel} severity={msg.severity:.2f} urgency={msg.urgency}\n"
            f"{msg.description}{context_part}"
        )

    def _format_episodic_block(self, episodes: list[str]) -> str:
        return "[SYSTEM_MEMORY_EPISODIC]\n\n" + "\n---\n".join(episodes)
