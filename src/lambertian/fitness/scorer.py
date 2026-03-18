"""IS-13.1 Fitness scorer — incremental and post-mortem computation."""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lambertian.configuration.universe_config import Config
from lambertian.fitness.cursor_state import FitnessCursorState, FitnessCursorStore
from lambertian.fitness.event_reader import EventStreamReader
from lambertian.fitness.formula import FitnessInputs
from lambertian.fitness.pain_reader import PainHistoryReader
from lambertian.fitness.registry import FitnessFunctionRegistry

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FitnessScore:
    turn_number: int
    score: float
    lifespan: int
    meaningful_event_count: int
    cumulative_pain: float
    computed_at: str  # ISO 8601 UTC


class FitnessScorer:
    def __init__(
        self,
        config: Config,
        registry: FitnessFunctionRegistry,
        cursor_store: FitnessCursorStore,
        event_reader: EventStreamReader,
        pain_reader: PainHistoryReader,
        output_path: Path,
    ) -> None:
        self._config = config
        self._registry = registry
        self._cursor_store = cursor_store
        self._event_reader = event_reader
        self._pain_reader = pain_reader
        self._output_path = output_path

    def compute_running(self, current_turn: int) -> FitnessScore:
        """Incremental score update. IS-13.1."""
        state = self._cursor_store.read()

        new_events, new_event_cursor = self._event_reader.count_new_meaningful_events(
            state.event_stream_cursor
        )
        new_pain, new_pain_cursor = self._pain_reader.sum_new_pain(
            state.pain_history_cursor
        )

        cumulative_pain = state.cumulative_pain + new_pain
        meaningful_event_count = state.meaningful_event_count + new_events

        score = self._compute_score(current_turn, meaningful_event_count, cumulative_pain)

        new_state = FitnessCursorState(
            last_computed_turn=current_turn,
            cumulative_pain=cumulative_pain,
            pain_history_cursor=new_pain_cursor,
            event_stream_cursor=new_event_cursor,
            meaningful_event_count=meaningful_event_count,
            last_score=score,
        )
        self._cursor_store.write(new_state)

        result = FitnessScore(
            turn_number=current_turn,
            score=score,
            lifespan=current_turn,
            meaningful_event_count=meaningful_event_count,
            cumulative_pain=cumulative_pain,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write_score(result)
        return result

    def compute_postmortem(
        self,
        event_stream_dir: Path,
        pain_history_path: Path,
        final_turn: int,
    ) -> FitnessScore:
        """Full re-scan from scratch. IS-13.1."""
        # Collect all events*.jsonl files and sort — archives sort before events.jsonl
        total_events = 0
        if event_stream_dir.exists():
            all_event_files = sorted(
                event_stream_dir.glob("events*.jsonl"), key=lambda p: p.name
            )
            for event_file in all_event_files:
                file_reader = EventStreamReader(event_file.parent)
                # For archives, the filename isn't events.jsonl — use a temporary reader
                archive_reader = _SingleFileEventReader(event_file)
                count, _ = archive_reader.count_meaningful_events()
                total_events += count

        pain_reader = PainHistoryReader(pain_history_path)
        cumulative_pain, _ = pain_reader.sum_new_pain(0)

        score = self._compute_score(final_turn, total_events, cumulative_pain)

        result = FitnessScore(
            turn_number=final_turn,
            score=score,
            lifespan=final_turn,
            meaningful_event_count=total_events,
            cumulative_pain=cumulative_pain,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write_score(result)
        return result

    def _compute_score(
        self,
        turn: int,
        meaningful_event_count: int,
        cumulative_pain: float,
    ) -> float:
        fitness_cfg = self._config.fitness
        inputs = FitnessInputs(
            lifespan=turn,
            max_age=self._config.universe.max_age_turns,
            meaningful_event_count=meaningful_event_count,
            expected_events_per_100_turns=fitness_cfg.expected_events_per_100_turns,
            cumulative_pain=cumulative_pain,
            normalized_pain_baseline=fitness_cfg.normalized_pain_baseline,
            minimum_denominator=fitness_cfg.minimum_denominator,
        )
        fn = self._registry.get(fitness_cfg.active_function)
        return fn.compute(inputs)

    def _write_score(self, score: FitnessScore) -> None:
        """Atomically write output_path via os.replace()."""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._output_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(dataclasses.asdict(score)), encoding="utf-8")
        os.replace(tmp_path, self._output_path)


class _SingleFileEventReader:
    """Helper that reads meaningful events from a single named file (not necessarily events.jsonl)."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def count_meaningful_events(self) -> tuple[int, int]:
        """Read the file from byte 0 and count meaningful events."""
        from lambertian.fitness.event_reader import MEANINGFUL_EVENT_TYPES

        try:
            with open(self._file_path, "rb") as f:
                count = 0
                for raw_line in f:
                    try:
                        record: object = json.loads(raw_line)
                        if not isinstance(record, dict):
                            continue
                        event_type = record.get("event_type")
                        if event_type in MEANINGFUL_EVENT_TYPES:
                            count += 1
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        _log.warning(
                            "_SingleFileEventReader: skipping unparseable line in %s",
                            self._file_path,
                        )
                return count, f.tell()
        except FileNotFoundError:
            return 0, 0
