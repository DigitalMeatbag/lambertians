"""Integration tests — startup → turn execution → death trigger slice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from lambertian.configuration.universe_config import Config
from lambertian.contracts.compliance_records import ComplianceNoticeResponse
from lambertian.contracts.pain_records import PainMessage
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.cursor_state import FitnessCursorStore
from lambertian.fitness.event_reader import EventStreamReader
from lambertian.fitness.pain_reader import PainHistoryReader
from lambertian.fitness.registry import build_default_registry
from lambertian.fitness.scorer import FitnessScorer
from lambertian.lifecycle.death_record_reader import DeathRecordReader
from lambertian.memory_store.querier import NoOpMemoryQuerier
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
    self_prompt_gen = SelfPromptGenerator(config)
    block_assembler = PromptBlockAssembler(config)

    fitness_scorer = FitnessScorer(
        config=config,
        registry=build_default_registry(),
        cursor_store=FitnessCursorStore(fitness_state_path),
        event_reader=EventStreamReader(event_stream_dir),
        pain_reader=PainHistoryReader(pain_root / "pain_history.jsonl"),
        output_path=fitness_path,
    )

    pain_submitter = FilePainEventSubmitter(pain_root / "event_queue.jsonl")

    # Mock external services.
    mock_ollama = MagicMock()
    mock_ollama.chat.return_value = (
        "Hello, this is a test response with enough characters to avoid noop.",
        [],
    )

    mock_compliance = MagicMock()
    mock_compliance.get_pending_notice.return_value = ComplianceNoticeResponse(
        notice_present=False,
        notice_text=None,
        verdict_from_turn=None,
        tool_name=None,
        composite_score=None,
    )

    mock_gateway = MagicMock()
    mock_gateway.get_tool_catalog.return_value = []

    drain = pain_drain if pain_drain is not None else _EmptyDrain()

    return TurnEngine(
        config=config,
        event_log=event_log,
        pain_drain=drain,  # type: ignore[arg-type]
        death_reader=death_reader,
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

