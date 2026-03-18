"""Tests for ManifestWriter."""
from __future__ import annotations

import json
from pathlib import Path

from lambertian.graveyard.artifact_collector import HarvestArtifact
from lambertian.graveyard.manifest import HarvestManifest, ManifestWriter


def _make_manifest(**kwargs: object) -> HarvestManifest:
    defaults: dict[str, object] = dict(
        instance_id="test-001",
        death_trigger="max_age",
        death_timestamp="2024-01-01T00:00:00+00:00",
        harvest_start_time="2024-01-01T00:00:01+00:00",
        harvest_end_time="2024-01-01T00:00:02+00:00",
        harvest_duration_seconds=1.0,
        artifacts=[
            HarvestArtifact(source="/src/death.json", output="death.json", success=True, error=None)
        ],
        fitness_score=0.75,
        artifact_count=1,
        failed_artifacts=0,
    )
    defaults.update(kwargs)
    return HarvestManifest(**defaults)  # type: ignore[arg-type]


def test_manifest_writer_creates_manifest_json(tmp_path: Path) -> None:
    manifest = _make_manifest()
    writer = ManifestWriter()
    writer.write(manifest, tmp_path)
    assert (tmp_path / "manifest.json").exists()


def test_manifest_json_content_matches_fields(tmp_path: Path) -> None:
    manifest = _make_manifest()
    writer = ManifestWriter()
    writer.write(manifest, tmp_path)

    data = json.loads((tmp_path / "manifest.json").read_text())
    assert data["instance_id"] == "test-001"
    assert data["death_trigger"] == "max_age"
    assert data["fitness_score"] == 0.75
    assert data["artifact_count"] == 1
    assert data["failed_artifacts"] == 0
    assert isinstance(data["artifacts"], list)
    assert data["artifacts"][0]["output"] == "death.json"
    assert data["artifacts"][0]["success"] is True


def test_manifest_writer_no_tmp_file_left_behind(tmp_path: Path) -> None:
    manifest = _make_manifest()
    writer = ManifestWriter()
    writer.write(manifest, tmp_path)
    # Confirm atomic write: no .tmp file remains
    assert not (tmp_path / "manifest.tmp").exists()
    assert (tmp_path / "manifest.json").exists()


def test_manifest_writer_creates_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "output"
    manifest = _make_manifest()
    writer = ManifestWriter()
    writer.write(manifest, output_dir)
    assert (output_dir / "manifest.json").exists()

