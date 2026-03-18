"""Tests for ArtifactCollector."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from lambertian.graveyard.artifact_collector import ArtifactCollector


def _make_config(
    include_event_stream: bool = True,
    include_pain_event_history: bool = True,
    include_stress_history: bool = True,
    include_episodic_memory: bool = False,
    memory_root: str = "runtime/memory",
) -> object:
    config = MagicMock()
    config.graveyard.include_event_stream = include_event_stream
    config.graveyard.include_pain_event_history = include_pain_event_history
    config.graveyard.include_stress_history = include_stress_history
    config.graveyard.include_episodic_memory = include_episodic_memory
    config.paths.memory_root = memory_root
    return config


def _setup_runtime(runtime_base: Path) -> None:
    """Create a minimal runtime directory for testing."""
    (runtime_base / "pain").mkdir(parents=True)
    (runtime_base / "pain" / "death.json").write_text(
        json.dumps({"instance_id": "test-001", "trigger": "max_age"})
    )
    (runtime_base / "pain" / "pain_history.jsonl").write_text(
        '{"severity": 0.5}\n'
    )
    (runtime_base / "pain" / "stress_history.jsonl").write_text(
        '{"scalar": 0.3}\n'
    )
    (runtime_base / "event_stream").mkdir(parents=True)


def test_collect_all_death_record_success(tmp_path: Path) -> None:
    runtime_base = tmp_path / "runtime"
    _setup_runtime(runtime_base)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = _make_config(memory_root=str(runtime_base / "memory"))
    collector = ArtifactCollector(config, runtime_base)  # type: ignore[arg-type]
    artifacts = collector.collect_all(output_dir)

    death_artifacts = [a for a in artifacts if "death.json" in a.output]
    assert len(death_artifacts) == 1
    assert death_artifacts[0].success is True
    assert (output_dir / "death.json").exists()


def test_collect_all_missing_death_record_is_failure(tmp_path: Path) -> None:
    runtime_base = tmp_path / "runtime"
    runtime_base.mkdir(parents=True)
    (runtime_base / "pain").mkdir()
    (runtime_base / "event_stream").mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = _make_config(
        include_event_stream=False,
        include_pain_event_history=False,
        include_stress_history=False,
        memory_root=str(runtime_base / "memory"),
    )
    collector = ArtifactCollector(config, runtime_base)  # type: ignore[arg-type]
    artifacts = collector.collect_all(output_dir)

    death_artifacts = [a for a in artifacts if "death.json" in a.output]
    assert len(death_artifacts) == 1
    assert death_artifacts[0].success is False


def test_collect_event_stream_concatenates_in_sort_order(tmp_path: Path) -> None:
    """Archives (events.YYYYMMDDTHHMMSSZ.jsonl) must come before events.jsonl."""
    runtime_base = tmp_path / "runtime"
    _setup_runtime(runtime_base)

    event_dir = runtime_base / "event_stream"
    # Archive files — by ASCII sort, digits < lowercase 'e' so they sort first
    (event_dir / "events.20240101T000000Z.jsonl").write_bytes(b'{"seq": 1}\n')
    (event_dir / "events.20240102T000000Z.jsonl").write_bytes(b'{"seq": 2}\n')
    (event_dir / "events.jsonl").write_bytes(b'{"seq": 3}\n')

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = _make_config(
        include_pain_event_history=False,
        include_stress_history=False,
        memory_root=str(runtime_base / "memory"),
    )
    collector = ArtifactCollector(config, runtime_base)  # type: ignore[arg-type]
    artifacts = collector.collect_all(output_dir)

    stream_artifacts = [a for a in artifacts if "event_stream" in a.output]
    assert len(stream_artifacts) == 1
    assert stream_artifacts[0].success is True

    concatenated = (output_dir / "event_stream" / "events.jsonl").read_bytes()
    lines = [json.loads(ln) for ln in concatenated.strip().split(b"\n")]
    seqs = [ln["seq"] for ln in lines]
    assert seqs == [1, 2, 3]


def test_missing_source_file_produces_failure_artifact(tmp_path: Path) -> None:
    runtime_base = tmp_path / "runtime"
    runtime_base.mkdir(parents=True)
    (runtime_base / "pain").mkdir()
    (runtime_base / "event_stream").mkdir()
    # No death.json, no pain_history.jsonl, no stress_history.jsonl
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = _make_config(memory_root=str(runtime_base / "memory"))
    collector = ArtifactCollector(config, runtime_base)  # type: ignore[arg-type]
    artifacts = collector.collect_all(output_dir)

    failed = [a for a in artifacts if not a.success]
    # At minimum death.json, pain_history.jsonl, stress_history.jsonl should fail
    assert len(failed) >= 3
