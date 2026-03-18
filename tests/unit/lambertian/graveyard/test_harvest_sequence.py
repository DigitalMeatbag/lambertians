"""Tests for HarvestSequence."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from lambertian.contracts.pain_records import DeathRecord
from lambertian.fitness.scorer import FitnessScore
from lambertian.graveyard.artifact_collector import HarvestArtifact
from lambertian.graveyard.harvest_sequence import HarvestSequence
from lambertian.graveyard.manifest import HarvestManifest


def _make_death_record() -> DeathRecord:
    return DeathRecord(
        instance_id="test-001",
        trigger="max_age",
        trigger_value=1000.0,
        threshold_used=1000.0,
        turn_number=999,
        timestamp="2024-01-01T00:00:00+00:00",
    )


def _make_fitness_score() -> FitnessScore:
    return FitnessScore(
        turn_number=999,
        score=0.42,
        lifespan=999,
        meaningful_event_count=100,
        cumulative_pain=5.0,
        computed_at="2024-01-01T00:00:01+00:00",
    )


def _make_config(grace_seconds: int = 0) -> object:
    config = MagicMock()
    config.universe.normal_shutdown_grace_seconds = grace_seconds
    config.paths.graveyard_root = "runtime/graveyard"
    return config


def _make_sequence(
    tmp_path: Path,
    *,
    death: DeathRecord | None = None,
    fitness_score: FitnessScore | None = None,
    artifacts: list[HarvestArtifact] | None = None,
) -> tuple[HarvestSequence, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    config = _make_config()
    death_reader = MagicMock()
    death_reader.read.return_value = death or _make_death_record()
    event_log = MagicMock()
    artifact_collector = MagicMock()
    artifact_collector.collect_all.return_value = artifacts or [
        HarvestArtifact(source="src", output="death.json", success=True, error=None)
    ]
    fitness_scorer = MagicMock()
    fitness_scorer.compute_postmortem.return_value = fitness_score or _make_fitness_score()
    manifest_writer = MagicMock()

    runtime_base = tmp_path / "runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    graveyard_base = tmp_path / "graveyard"

    seq = HarvestSequence(
        config=config,  # type: ignore[arg-type]
        death_reader=death_reader,
        event_log=event_log,
        artifact_collector=artifact_collector,
        fitness_scorer=fitness_scorer,
        manifest_writer=manifest_writer,
        graveyard_output_base=graveyard_base,
        runtime_base=runtime_base,
    )
    return seq, death_reader, event_log, artifact_collector, fitness_scorer, manifest_writer


def test_execute_reads_death_record(tmp_path: Path) -> None:
    seq, death_reader, *_ = _make_sequence(tmp_path)
    seq.execute()
    death_reader.read.assert_called_once()


def test_execute_writes_harvest_start_event(tmp_path: Path) -> None:
    seq, _, event_log, *_ = _make_sequence(tmp_path)
    seq.execute()
    calls = [c for c in event_log.write_event.call_args_list if c[0][0] == "GRAVEYARD_HARVEST_START"]
    assert len(calls) == 1


def test_execute_calls_artifact_collector(tmp_path: Path) -> None:
    seq, _, _, artifact_collector, *_ = _make_sequence(tmp_path)
    seq.execute()
    artifact_collector.collect_all.assert_called_once()


def test_execute_calls_fitness_scorer_postmortem(tmp_path: Path) -> None:
    seq, _, _, _, fitness_scorer, _ = _make_sequence(tmp_path)
    seq.execute()
    fitness_scorer.compute_postmortem.assert_called_once()


def test_execute_calls_manifest_writer(tmp_path: Path) -> None:
    seq, _, _, _, _, manifest_writer = _make_sequence(tmp_path)
    seq.execute()
    manifest_writer.write.assert_called_once()
    written_manifest = manifest_writer.write.call_args[0][0]
    assert isinstance(written_manifest, HarvestManifest)


def test_execute_writes_harvest_complete_event(tmp_path: Path) -> None:
    seq, _, event_log, *_ = _make_sequence(tmp_path)
    seq.execute()
    calls = [c for c in event_log.write_event.call_args_list if c[0][0] == "GRAVEYARD_HARVEST_COMPLETE"]
    assert len(calls) == 1


def test_execute_writes_sentinel_file(tmp_path: Path) -> None:
    seq, *_ = _make_sequence(tmp_path)
    runtime_base = tmp_path / "runtime"
    seq.execute()
    sentinel = runtime_base / "graveyard" / "harvest_complete"
    assert sentinel.exists()
    data = json.loads(sentinel.read_text())
    assert data["instance_id"] == "test-001"


def test_execute_does_not_call_sys_exit(tmp_path: Path) -> None:
    """execute() must return normally — not call sys.exit()."""
    import sys

    seq, *_ = _make_sequence(tmp_path)
    with patch.object(sys, "exit") as mock_exit:
        seq.execute()
        mock_exit.assert_not_called()


def test_execute_raises_on_missing_death_record(tmp_path: Path) -> None:
    seq, death_reader, *_ = _make_sequence(tmp_path)
    death_reader.read.return_value = None
    import pytest

    with pytest.raises(RuntimeError, match="no death record"):
        seq.execute()
