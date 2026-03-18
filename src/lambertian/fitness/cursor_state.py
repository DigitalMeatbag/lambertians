"""IS-13 fitness cursor state persistence."""
from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FitnessCursorState:
    last_computed_turn: int
    cumulative_pain: float
    pain_history_cursor: int
    event_stream_cursor: int
    meaningful_event_count: int
    last_score: float
    # Cumulative per-type event counts for quality-weighted fitness (IS-13 Phase 2).
    # Absent in cursor files written by Phase 1 instances — defaults to {} on read.
    event_type_histogram: dict[str, int] = field(default_factory=dict)


class FitnessCursorStore:
    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path

    def read(self) -> FitnessCursorState:
        """Return persisted state, or zero-initialized state if file is absent."""
        if not self._state_path.exists():
            return FitnessCursorState(
                last_computed_turn=0,
                cumulative_pain=0.0,
                pain_history_cursor=0,
                event_stream_cursor=0,
                meaningful_event_count=0,
                last_score=0.0,
            )
        raw: object = json.loads(self._state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return FitnessCursorState(
                last_computed_turn=0,
                cumulative_pain=0.0,
                pain_history_cursor=0,
                event_stream_cursor=0,
                meaningful_event_count=0,
                last_score=0.0,
            )
        # Any is at the JSON parse boundary — values are validated by explicit field access
        raw_histogram = raw.get("event_type_histogram", {})
        histogram: dict[str, int] = (
            {str(k): int(v) for k, v in raw_histogram.items()}
            if isinstance(raw_histogram, dict)
            else {}
        )
        return FitnessCursorState(
            last_computed_turn=int(raw.get("last_computed_turn", 0)),
            cumulative_pain=float(raw.get("cumulative_pain", 0.0)),
            pain_history_cursor=int(raw.get("pain_history_cursor", 0)),
            event_stream_cursor=int(raw.get("event_stream_cursor", 0)),
            meaningful_event_count=int(raw.get("meaningful_event_count", 0)),
            last_score=float(raw.get("last_score", 0.0)),
            event_type_histogram=histogram,
        )

    def write(self, state: FitnessCursorState) -> None:
        """Atomically write state to disk via temp file + os.replace()."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._state_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(dataclasses.asdict(state)), encoding="utf-8"
        )
        os.replace(tmp_path, self._state_path)
