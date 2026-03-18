"""Shared fixtures for Phase 1 integration validation tests."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from lambertian.configuration.loader import load_config
from lambertian.configuration.universe_config import Config

# Navigate from tests/integration/lambertian/ up to repo root.
_REPO_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    """Minimal Config with all file-system paths redirected to tmp_path."""
    base = load_config(_REPO_ROOT / "config" / "universe.toml")

    runtime = tmp_path / "runtime"

    new_paths = dataclasses.replace(
        base.paths,
        runtime_root=str(runtime),
        event_stream_file=str(runtime / "event_stream" / "events.jsonl"),
        memory_root=str(runtime / "memory"),
        pain_root=str(runtime / "pain"),
        graveyard_root=str(tmp_path / "graveyard_output"),
        fitness_file=str(runtime / "fitness" / "score.json"),
        self_model_file=str(runtime / "self" / "self_model.json"),
    )
    new_universe = dataclasses.replace(
        base.universe,
        max_age_turns=5,
        normal_shutdown_grace_seconds=0,
    )
    new_turn = dataclasses.replace(
        base.turn,
        loop_sleep_seconds=0.0,
    )
    new_fitness = dataclasses.replace(
        base.fitness,
        compute_running_score=True,
    )
    # flush_interval_seconds=0 ensures writes are flushed immediately in tests
    # (the default 1s interval means events are buffered during a fast test turn).
    new_event_stream = dataclasses.replace(
        base.event_stream,
        flush_interval_seconds=0,
    )
    return dataclasses.replace(
        base,
        paths=new_paths,
        universe=new_universe,
        turn=new_turn,
        fitness=new_fitness,
        event_stream=new_event_stream,
    )

