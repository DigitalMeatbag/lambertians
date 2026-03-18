"""Integration tests — graveyard poll loop → harvest sequence slice."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lambertian.configuration.universe_config import Config
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.scorer import FitnessScore, FitnessScorer
from lambertian.graveyard.artifact_collector import ArtifactCollector
from lambertian.graveyard.harvest_sequence import HarvestSequence
from lambertian.graveyard.manifest import ManifestWriter
from lambertian.graveyard.poll_loop import GraveyardPollLoop
from lambertian.lifecycle.death_record_reader import DeathRecordReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEATH_RECORD: dict[str, object] = {
    "instance_id": "test-inst-001",
    "trigger": "critical_pain",
    "trigger_value": 42.0,
    "threshold_used": 0.95,
    "turn_number": 3,
    "timestamp": "2025-01-01T00:00:00Z",
}


def _write_death_record(pain_root: Path, record: dict[str, object] | None = None) -> None:
    pain_root.mkdir(parents=True, exist_ok=True)
    data = record if record is not None else _DEATH_RECORD
    (pain_root / "death.json").write_text(json.dumps(data), encoding="utf-8")


def _make_dummy_fitness_score() -> FitnessScore:
    return FitnessScore(
        turn_number=3,
        score=0.5,
        lifespan=3,
        meaningful_event_count=2,
        cumulative_pain=0.1,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_harvest_sequence(
    config: Config,
    runtime: Path,
    fitness_score: FitnessScore | None = None,
) -> HarvestSequence:
    graveyard_output = Path(config.paths.graveyard_root)
    pain_root = runtime / "pain"

    death_reader = DeathRecordReader(pain_root / "death.json")
    event_log = EventLogWriter(config)
    artifact_collector = ArtifactCollector(config, runtime)
    manifest_writer = ManifestWriter()

    mock_scorer = MagicMock(spec=FitnessScorer)
    result = fitness_score if fitness_score is not None else _make_dummy_fitness_score()
    mock_scorer.compute_postmortem.return_value = result

    return HarvestSequence(
        config=config,
        death_reader=death_reader,
        event_log=event_log,
        artifact_collector=artifact_collector,
        fitness_scorer=mock_scorer,  # type: ignore[arg-type]
        manifest_writer=manifest_writer,
        graveyard_output_base=graveyard_output,
        runtime_base=runtime,
    )


def _find_harvest_dir(graveyard_root: Path) -> Path | None:
    """Return the first harvest output directory if it exists."""
    if not graveyard_root.exists():
        return None
    for child in graveyard_root.iterdir():
        if child.is_dir():
            return child
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGraveyardHarvestOnDeathRecord:
    def test_graveyard_harvests_on_death_record(
        self, config: Config, tmp_path: Path
    ) -> None:
        """GraveyardPollLoop detects death record and harvest sequence runs to completion."""
        runtime = Path(config.paths.runtime_root)
        pain_root = runtime / "pain"
        event_stream_dir = Path(config.paths.event_stream_file).parent

        # Pre-write death record.
        _write_death_record(pain_root)

        # Seed an event stream so event_stream artifact collection finds something.
        event_stream_dir.mkdir(parents=True, exist_ok=True)
        mock_event = {
            "event_type": "STARTUP",
            "event_id": "aaa",
            "instance_id": "test-inst-001",
            "timestamp": "2025-01-01T00:00:00Z",
            "turn_number": 0,
            "source_service": "agent",
        }
        (event_stream_dir / "events.jsonl").write_text(
            json.dumps(mock_event) + "\n", encoding="utf-8"
        )

        # Memory dir must exist for memory snapshot collection.
        (runtime / "memory").mkdir(parents=True, exist_ok=True)

        harvest_seq = _build_harvest_sequence(config, runtime)
        death_reader = DeathRecordReader(pain_root / "death.json")
        sentinel_path = Path(config.paths.graveyard_root) / "harvest_complete"
        poll_loop = GraveyardPollLoop(
            death_reader=death_reader,
            harvest_sequence=harvest_seq,
            sentinel_path=sentinel_path,
        )

        # run() loops forever. Let the harvest's grace-period sleep pass (call 1),
        # then raise StopIteration on the loop's idle sleep (call 2+).
        _calls = 0

        def _mock_sleep(s: float) -> None:
            nonlocal _calls
            _calls += 1
            if _calls >= 2:
                raise StopIteration

        with patch("time.sleep", side_effect=_mock_sleep):
            with pytest.raises(StopIteration):
                poll_loop.run()

        graveyard_root = Path(config.paths.graveyard_root)
        harvest_dir = _find_harvest_dir(graveyard_root)
        assert harvest_dir is not None, "harvest output directory must be created"

        manifest_path = harvest_dir / "manifest.json"
        assert manifest_path.exists(), "manifest.json must exist in harvest directory"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest.get("death_trigger") == "critical_pain"
        assert isinstance(manifest.get("artifact_count"), int)
        assert manifest["artifact_count"] >= 1

    def test_harvest_complete_sentinel_written(
        self, config: Config, tmp_path: Path
    ) -> None:
        """sentinel file runtime/graveyard/harvest_complete is written after harvest."""
        runtime = Path(config.paths.runtime_root)
        pain_root = runtime / "pain"
        event_stream_dir = Path(config.paths.event_stream_file).parent

        _write_death_record(pain_root)
        event_stream_dir.mkdir(parents=True, exist_ok=True)
        (event_stream_dir / "events.jsonl").write_text("", encoding="utf-8")
        (runtime / "memory").mkdir(parents=True, exist_ok=True)

        harvest_seq = _build_harvest_sequence(config, runtime)
        death_reader = DeathRecordReader(pain_root / "death.json")
        sentinel_path = Path(config.paths.graveyard_root) / "harvest_complete"
        poll_loop = GraveyardPollLoop(
            death_reader=death_reader,
            harvest_sequence=harvest_seq,
            sentinel_path=sentinel_path,
        )

        _calls = 0

        def _mock_sleep(s: float) -> None:
            nonlocal _calls
            _calls += 1
            if _calls >= 2:
                raise StopIteration

        with patch("time.sleep", side_effect=_mock_sleep):
            with pytest.raises(StopIteration):
                poll_loop.run()

        sentinel = runtime / "graveyard" / "harvest_complete"
        assert sentinel.exists(), "harvest_complete sentinel must be written"


class TestGraveyardManifestFitnessScore:
    def test_manifest_includes_fitness_score(
        self, config: Config, tmp_path: Path
    ) -> None:
        """manifest.json contains the fitness_score returned by compute_postmortem."""
        runtime = Path(config.paths.runtime_root)
        pain_root = runtime / "pain"
        event_stream_dir = Path(config.paths.event_stream_file).parent

        _write_death_record(pain_root)
        event_stream_dir.mkdir(parents=True, exist_ok=True)
        (event_stream_dir / "events.jsonl").write_text("", encoding="utf-8")
        (runtime / "memory").mkdir(parents=True, exist_ok=True)

        target_score = FitnessScore(
            turn_number=3,
            score=0.75,
            lifespan=3,
            meaningful_event_count=5,
            cumulative_pain=0.2,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

        harvest_seq = _build_harvest_sequence(config, runtime, fitness_score=target_score)
        death_reader = DeathRecordReader(pain_root / "death.json")
        sentinel_path = Path(config.paths.graveyard_root) / "harvest_complete"
        poll_loop = GraveyardPollLoop(
            death_reader=death_reader,
            harvest_sequence=harvest_seq,
            sentinel_path=sentinel_path,
        )

        _calls = 0

        def _mock_sleep(s: float) -> None:
            nonlocal _calls
            _calls += 1
            if _calls >= 2:
                raise StopIteration

        with patch("time.sleep", side_effect=_mock_sleep):
            with pytest.raises(StopIteration):
                poll_loop.run()

        graveyard_root = Path(config.paths.graveyard_root)
        harvest_dir = _find_harvest_dir(graveyard_root)
        assert harvest_dir is not None

        manifest = json.loads((harvest_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest.get("fitness_score") == pytest.approx(0.75)

