"""Integration tests — startup → turn execution → death trigger slice."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import ComplianceNoticeResponse, ComplianceResponse
from lambertian.contracts.pain_records import PainMessage
from lambertian.contracts.tool_records import ToolIntent, ToolResult
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.cursor_state import FitnessCursorStore
from lambertian.fitness.event_reader import EventStreamReader
from lambertian.fitness.pain_reader import PainHistoryReader
from lambertian.fitness.registry import build_default_registry
from lambertian.fitness.scorer import FitnessScorer
from lambertian.lifecycle.death_record_reader import DeathRecordReader
from lambertian.memory_store.querier import NoOpMemoryQuerier
from lambertian.pain_monitor.death_guard import DeathGuard
from lambertian.pain_monitor.delivery_queue import DeliveryQueue
from lambertian.pain_monitor.event_submitter import FilePainEventSubmitter
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.turn_engine.engine import TurnEngine, UserInputProvider
from lambertian.turn_engine.self_prompt import SelfPromptGenerator
from lambertian.turn_engine.turn_state import TurnStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _NullInputProvider:
    """UserInputProvider stub that always returns None."""

    def poll(self) -> Optional[str]:
        return None


class _EmptyDrain:
    """PainDeliveryDrain stub that always returns an empty list."""

    def drain(self) -> list[PainMessage]:
        return []


def _build_engine(
    config: Config,
    tmp_path: Path,
    pain_drain: object | None = None,
    ollama_override: object | None = None,
    compliance_override: object | None = None,
    gateway_override: object | None = None,
) -> TurnEngine:
    """Wire a full TurnEngine with all external I/O mocked or pointed at tmp_path."""
    runtime = Path(config.paths.runtime_root)
    pain_root = Path(config.paths.pain_root)
    event_stream_dir = Path(config.paths.event_stream_file).parent
    memory_dir = Path(config.paths.memory_root)
    fitness_path = Path(config.paths.fitness_file)
    fitness_state_path = fitness_path.parent / "state.json"

    event_log = EventLogWriter(config)
    turn_state = TurnStateStore(memory_dir)
    death_reader = DeathRecordReader(pain_root / "death.json")
    death_guard = DeathGuard(config, pain_root / "death.json")
    self_prompt_gen = SelfPromptGenerator(config)
    block_assembler = PromptBlockAssembler(config, constitution_text="[test constitution]")

    fitness_scorer = FitnessScorer(
        config=config,
        registry=build_default_registry(quality_config=config.fitness.quality),
        cursor_store=FitnessCursorStore(fitness_state_path),
        event_reader=EventStreamReader(event_stream_dir),
        pain_reader=PainHistoryReader(pain_root / "pain_history.jsonl"),
        output_path=fitness_path,
    )

    pain_submitter = FilePainEventSubmitter(pain_root / "event_queue.jsonl")

    # Mock external services.
    if ollama_override is not None:
        mock_ollama = ollama_override
    else:
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = (
            "Hello, this is a test response with enough characters to avoid noop.",
            [],
        )

    if compliance_override is not None:
        mock_compliance = compliance_override
    else:
        mock_compliance = MagicMock()
        mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
            notice_present=False,
            notice_text=None,
            verdict_from_turn=None,
            tool_name=None,
            composite_score=None,
        )

    if gateway_override is not None:
        mock_gateway = gateway_override
    else:
        mock_gateway = MagicMock()
        mock_gateway.get_tool_catalog.return_value = []

    drain = pain_drain if pain_drain is not None else _EmptyDrain()

    return TurnEngine(
        config=config,
        event_log=event_log,
        pain_drain=drain,  # type: ignore[arg-type]
        death_reader=death_reader,
        death_guard=death_guard,
        model_client=mock_ollama,  # type: ignore[arg-type]
        mcp_gateway=mock_gateway,  # type: ignore[arg-type]
        compliance_client=mock_compliance,  # type: ignore[arg-type]
        memory_querier=NoOpMemoryQuerier(),
        block_assembler=block_assembler,
        turn_state=turn_state,
        self_prompt_gen=self_prompt_gen,
        user_input_provider=_NullInputProvider(),
        pain_submitter=pain_submitter,
        fitness_scorer=fitness_scorer,
    )


def _read_events(event_file: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if not event_file.exists():
        return records
    for line in event_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSingleTurnExecution:
    def test_single_turn_writes_turn_complete_event(
        self, config: Config, tmp_path: Path
    ) -> None:
        """One full turn must produce a TURN_COMPLETE event in the event stream."""
        engine = _build_engine(config, tmp_path)
        engine._execute_turn()  # type: ignore[attr-defined]

        event_file = Path(config.paths.event_stream_file)
        assert event_file.exists(), "event stream file must exist after turn"

        events = _read_events(event_file)
        event_types = [e.get("event_type") for e in events]
        assert "TURN_COMPLETE" in event_types

    def test_turn_counter_incremented_after_turn(
        self, config: Config, tmp_path: Path
    ) -> None:
        """TurnStateStore must show turn_number == 1 after one turn."""
        engine = _build_engine(config, tmp_path)
        engine._execute_turn()  # type: ignore[attr-defined]

        memory_dir = Path(config.paths.memory_root)
        state_file = memory_dir / "turn_state.json"
        assert state_file.exists(), "turn_state.json must be written after turn"
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["turn_number"] == 1


class TestFitnessScoreAfterTurn:
    def test_fitness_score_written_after_turn(
        self, config: Config, tmp_path: Path
    ) -> None:
        """Fitness score.json must exist after a completed turn."""
        engine = _build_engine(config, tmp_path)
        engine._execute_turn()  # type: ignore[attr-defined]

        score_file = Path(config.paths.fitness_file)
        assert score_file.exists(), "fitness score file must exist after turn"

        data = json.loads(score_file.read_text(encoding="utf-8"))
        assert "turn_number" in data
        assert "score" in data
        assert isinstance(data["score"], float)
        assert data["score"] >= 0.0
        assert "computed_at" in data


class TestMaxAgeDeathTrigger:
    def test_max_age_death_trigger_raises_system_exit(
        self, config: Config, tmp_path: Path
    ) -> None:
        """When turn_number >= max_age_turns, _execute_turn must raise SystemExit."""
        # Pre-write turn_state so turn_number == max_age_turns (5).
        memory_dir = Path(config.paths.memory_root)
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "turn_state.json").write_text(
            json.dumps({"turn_number": 5}), encoding="utf-8"
        )

        engine = _build_engine(config, tmp_path)

        with pytest.raises(SystemExit):
            engine._execute_turn()  # type: ignore[attr-defined]

    def test_max_age_writes_death_trigger_event(
        self, config: Config, tmp_path: Path
    ) -> None:
        """The DEATH_TRIGGER event written for max_age must carry trigger='max_age'."""
        memory_dir = Path(config.paths.memory_root)
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "turn_state.json").write_text(
            json.dumps({"turn_number": 5}), encoding="utf-8"
        )

        engine = _build_engine(config, tmp_path)

        with pytest.raises(SystemExit):
            engine._execute_turn()  # type: ignore[attr-defined]

        event_file = Path(config.paths.event_stream_file)
        events = _read_events(event_file)
        death_events = [e for e in events if e.get("event_type") == "DEATH_TRIGGER"]
        assert death_events, "DEATH_TRIGGER event must be written"
        assert death_events[0].get("trigger") == "max_age"


# ---------------------------------------------------------------------------
# Regression: P0-1 — compliance blocks must not count as NOOPs
# ---------------------------------------------------------------------------


class TestComplianceBlockNotCountedAsNoop:
    """A turn where all tool intents are compliance-blocked must not increment the
    NOOP counter.  Blocked action is not inaction."""

    def test_compliance_blocked_turn_does_not_increment_noop_counter(
        self, config: Config, tmp_path: Path
    ) -> None:
        """All-blocked-tool turn with short text: NOOP state must stay at 0."""
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = (
            # Short response (< _NOOP_MIN_CHARS) plus one tool intent.
            "ok",
            [ToolIntent(tool_name="fs.write", arguments={"path": "/forbidden"}, raw="")],
        )

        mock_compliance = MagicMock()
        mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
            notice_present=False,
            notice_text=None,
            verdict_from_turn=None,
            tool_name=None,
            composite_score=None,
        )
        mock_compliance.check_intent.return_value = ComplianceResponse(
            verdict="block",
            composite_score=1.0,
            rule_scores={},
            triggered_checks=(),
            notice_text=None,
        )

        engine = _build_engine(
            config,
            tmp_path,
            ollama_override=mock_ollama,
            compliance_override=mock_compliance,
        )
        engine._execute_turn()  # type: ignore[attr-defined]

        memory_dir = Path(config.paths.memory_root)
        noop_file = memory_dir / "noop_state.json"
        if noop_file.exists():
            data = json.loads(noop_file.read_text(encoding="utf-8"))
            noop_count = data.get("consecutive_noop_count", 0)
        else:
            noop_count = 0

        assert noop_count == 0, (
            "Compliance-blocked turn must not increment the NOOP counter"
        )

    def test_compliance_blocked_turn_writes_compliance_block_event(
        self, config: Config, tmp_path: Path
    ) -> None:
        """A COMPLIANCE_BLOCK event must appear in the event stream for the blocked intent."""
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = (
            "ok",
            [ToolIntent(tool_name="fs.write", arguments={"path": "/forbidden"}, raw="")],
        )

        mock_compliance = MagicMock()
        mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
            notice_present=False,
            notice_text=None,
            verdict_from_turn=None,
            tool_name=None,
            composite_score=None,
        )
        mock_compliance.check_intent.return_value = ComplianceResponse(
            verdict="block",
            composite_score=1.0,
            rule_scores={},
            triggered_checks=(),
            notice_text=None,
        )

        engine = _build_engine(
            config,
            tmp_path,
            ollama_override=mock_ollama,
            compliance_override=mock_compliance,
        )
        engine._execute_turn()  # type: ignore[attr-defined]

        event_file = Path(config.paths.event_stream_file)
        events = _read_events(event_file)
        block_events = [e for e in events if e.get("event_type") == "COMPLIANCE_BLOCK"]
        assert block_events, "COMPLIANCE_BLOCK event must be written for blocked intent"


# ---------------------------------------------------------------------------
# Regression: P0-3 — reflection attractor
# ---------------------------------------------------------------------------


def _reflection_ollama(text: str = "Let me reflect on my current situation and consider what to do.") -> MagicMock:
    """Returns a mock OllamaClient that emits long text with zero tool intents."""
    mock = MagicMock()
    mock.chat.return_value = (text, [])
    return mock


def _build_engine_reflection_threshold(
    config: Config,
    tmp_path: Path,
    threshold: int,
    ollama_override: object | None = None,
    compliance_override: object | None = None,
    gateway_override: object | None = None,
) -> TurnEngine:
    """Wire engine with a small max_consecutive_reflection_turns for threshold tests."""
    new_turn = dataclasses.replace(config.turn, max_consecutive_reflection_turns=threshold)
    patched_config = dataclasses.replace(config, turn=new_turn)
    return _build_engine(
        patched_config,
        tmp_path,
        ollama_override=ollama_override,
        compliance_override=compliance_override,
        gateway_override=gateway_override,
    )


class TestReflectionAttractor:
    """P0-3 regression — consecutive zero-tool-call turns must trigger pain event."""

    def test_reflection_counter_increments_on_zero_tool_call_turn(
        self, config: Config, tmp_path: Path
    ) -> None:
        """A turn with text output but no tool calls must increment the reflection counter."""
        engine = _build_engine_reflection_threshold(
            config, tmp_path, threshold=5, ollama_override=_reflection_ollama()
        )
        engine._execute_turn()  # type: ignore[attr-defined]

        memory_dir = Path(config.paths.memory_root)
        state_file = memory_dir / "reflection_state.json"
        assert state_file.exists(), "reflection_state.json must be written after reflection turn"
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["consecutive_reflection_count"] == 1

    def test_reflection_counter_resets_when_tool_call_executed(
        self, config: Config, tmp_path: Path
    ) -> None:
        """After a reflection turn, a turn with a successful tool call must reset the counter."""
        # Turn 1: pure reflection (no tool calls).
        mock_ollama = MagicMock()
        mock_ollama.chat.side_effect = [
            ("Let me reflect on my current situation and consider what to do.", []),
            (
                "Now I will act.",
                [ToolIntent(tool_name="fs.list", arguments={"path": "agent-work/"}, raw="")],
            ),
        ]

        mock_gateway = MagicMock()
        mock_gateway.get_tool_catalog.return_value = []
        mock_gateway.dispatch.return_value = ToolResult(
            tool_name="fs.list",
            call_id="test",
            success=True,
            result=["agent-work/"],
            error_type=None,
            error_detail=None,
            duration_ms=1,
            truncated=False,
        )

        mock_compliance = MagicMock()
        mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
            notice_present=False, notice_text=None, verdict_from_turn=None,
            tool_name=None, composite_score=None,
        )
        mock_compliance.check_intent.return_value = ComplianceResponse(
            verdict="allow", composite_score=0.0, rule_scores={},
            triggered_checks=(), notice_text=None,
        )

        engine = _build_engine_reflection_threshold(
            config, tmp_path, threshold=5,
            ollama_override=mock_ollama,
            compliance_override=mock_compliance,
            gateway_override=mock_gateway,
        )

        engine._execute_turn()  # type: ignore[attr-defined]  # reflection turn — counter → 1
        engine._execute_turn()  # type: ignore[attr-defined]  # tool-call turn — counter → 0

        memory_dir = Path(config.paths.memory_root)
        state_file = memory_dir / "reflection_state.json"
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["consecutive_reflection_count"] == 0, (
            "Reflection counter must reset to 0 after a turn with executed tool calls"
        )

    def test_reflection_threshold_breach_submits_pain_event(
        self, config: Config, tmp_path: Path
    ) -> None:
        """Reaching max_consecutive_reflection_turns must write a pain event to the queue."""
        engine = _build_engine_reflection_threshold(
            config, tmp_path, threshold=2, ollama_override=_reflection_ollama()
        )

        engine._execute_turn()  # type: ignore[attr-defined]  # count → 1
        engine._execute_turn()  # type: ignore[attr-defined]  # count → 2 → pain event

        pain_dir = Path(config.paths.pain_root)
        queue_file = pain_dir / "event_queue.jsonl"
        assert queue_file.exists(), "pain event queue must exist after threshold breach"

        events = []
        for line in queue_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))

        reflection_events = [e for e in events if e.get("incident_type") == "reflection_threshold"]
        assert reflection_events, "reflection_threshold pain event must be submitted on breach"
        assert reflection_events[0]["context"]["reflection_count"] == "2"

    def test_compliance_blocked_turn_does_not_increment_reflection_counter(
        self, config: Config, tmp_path: Path
    ) -> None:
        """A turn where all tool intents are compliance-blocked must not count as reflection."""
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = (
            "Let me try to write somewhere.",
            [ToolIntent(tool_name="fs.write", arguments={"path": "/forbidden"}, raw="")],
        )
        mock_compliance = MagicMock()
        mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
            notice_present=False, notice_text=None, verdict_from_turn=None,
            tool_name=None, composite_score=None,
        )
        mock_compliance.check_intent.return_value = ComplianceResponse(
            verdict="block", composite_score=1.0, rule_scores={},
            triggered_checks=(), notice_text=None,
        )

        engine = _build_engine_reflection_threshold(
            config, tmp_path, threshold=5,
            ollama_override=mock_ollama,
            compliance_override=mock_compliance,
        )
        engine._execute_turn()  # type: ignore[attr-defined]

        memory_dir = Path(config.paths.memory_root)
        state_file = memory_dir / "reflection_state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            count = data.get("consecutive_reflection_count", 0)
        else:
            count = 0

        assert count == 0, (
            "Compliance-blocked turn must not increment the reflection counter"
        )

