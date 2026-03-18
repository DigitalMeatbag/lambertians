"""Graveyard entrypoint — wires dependencies and starts the harvest monitor process."""
from __future__ import annotations

from pathlib import Path

from lambertian.configuration.loader import load_config
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.cursor_state import FitnessCursorStore
from lambertian.fitness.event_reader import EventStreamReader
from lambertian.fitness.pain_reader import PainHistoryReader
from lambertian.fitness.registry import build_default_registry
from lambertian.fitness.scorer import FitnessScorer
from lambertian.graveyard.artifact_collector import ArtifactCollector
from lambertian.graveyard.harvest_sequence import HarvestSequence
from lambertian.graveyard.manifest import ManifestWriter
from lambertian.graveyard.poll_loop import GraveyardPollLoop
from lambertian.lifecycle.death_record_reader import DeathRecordReader


def main() -> None:
    config = load_config(Path("config/universe.toml"))
    runtime_base = Path("runtime")

    death_reader = DeathRecordReader(runtime_base / "pain" / "death.json")
    event_log = EventLogWriter(config)

    registry = build_default_registry()
    cursor_store = FitnessCursorStore(runtime_base / "fitness" / "state.json")
    event_reader = EventStreamReader(runtime_base / "event_stream")
    pain_reader = PainHistoryReader(runtime_base / "pain" / "pain_history.jsonl")
    fitness_scorer = FitnessScorer(
        config,
        registry,
        cursor_store,
        event_reader,
        pain_reader,
        runtime_base / "fitness" / "score.json",
    )

    artifact_collector = ArtifactCollector(config, runtime_base)
    manifest_writer = ManifestWriter()
    harvest = HarvestSequence(
        config,
        death_reader,
        event_log,
        artifact_collector,
        fitness_scorer,
        manifest_writer,
        Path(config.paths.graveyard_root),
        runtime_base,
    )

    poll = GraveyardPollLoop(death_reader, harvest)
    poll.run()
