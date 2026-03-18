"""IS-12 Harvest manifest — records what was collected and how the harvest went."""
from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lambertian.graveyard.artifact_collector import HarvestArtifact


@dataclass(frozen=True)
class HarvestManifest:
    instance_id: str
    death_trigger: str
    death_timestamp: str
    harvest_start_time: str
    harvest_end_time: str
    harvest_duration_seconds: float
    artifacts: list[HarvestArtifact]
    fitness_score: Optional[float]
    artifact_count: int
    failed_artifacts: int


class ManifestWriter:
    def write(self, manifest: HarvestManifest, output_dir: Path) -> None:
        """Atomically write manifest.json to output_dir using os.replace()."""
        output_dir.mkdir(parents=True, exist_ok=True)
        dst = output_dir / "manifest.json"
        tmp_path = output_dir / "manifest.tmp"
        data = dataclasses.asdict(manifest)
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_path, dst)
