"""IS-12.3 Harvest sequence — 10-step graveyard harvest execution."""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lambertian.configuration.universe_config import Config
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.scorer import FitnessScorer
from lambertian.graveyard.artifact_collector import ArtifactCollector
from lambertian.graveyard.manifest import HarvestManifest, ManifestWriter
from lambertian.graveyard.workspace_reset import WorkspaceReset
from lambertian.lifecycle.death_record_reader import DeathRecordReader

_log = logging.getLogger(__name__)


class HarvestSequence:
    """Executes the 10-step harvest sequence. IS-12.3."""

    def __init__(
        self,
        config: Config,
        death_reader: DeathRecordReader,
        event_log: EventLogWriter,
        artifact_collector: ArtifactCollector,
        fitness_scorer: FitnessScorer,
        manifest_writer: ManifestWriter,
        graveyard_output_base: Path,
        runtime_base: Path,
        workspace_reset: WorkspaceReset,
    ) -> None:
        self._config = config
        self._death_reader = death_reader
        self._event_log = event_log
        self._artifact_collector = artifact_collector
        self._fitness_scorer = fitness_scorer
        self._manifest_writer = manifest_writer
        self._graveyard_output_base = graveyard_output_base
        self._runtime_base = runtime_base
        self._workspace_reset = workspace_reset

    def execute(self) -> None:
        """Run all 10 steps. IS-12.3."""
        start_time = time.monotonic()
        start_timestamp = datetime.now(timezone.utc).isoformat()

        # Step 1: read death record, write GRAVEYARD_HARVEST_START
        death = self._death_reader.read()
        if death is None:
            raise RuntimeError("Harvest triggered but no death record found")

        self._event_log.write_event(
            "GRAVEYARD_HARVEST_START",
            0,
            "graveyard",
            {
                "death_trigger": death.trigger,
                "death_timestamp": death.timestamp,
            },
        )

        # Step 2: sleep grace period
        time.sleep(self._config.universe.normal_shutdown_grace_seconds)

        # Step 3: create output directory
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = self._graveyard_output_base / f"{death.instance_id}_{ts}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: collect artifacts
        artifacts = self._artifact_collector.collect_all(output_dir)

        # Step 5: compute post-mortem fitness
        fitness_score: Optional[float] = None
        try:
            score_result = self._fitness_scorer.compute_postmortem(
                event_stream_dir=self._runtime_base / "event_stream",
                pain_history_path=self._runtime_base / "pain" / "pain_history.jsonl",
                final_turn=death.turn_number,
            )
            fitness_score = score_result.score
            (output_dir / "fitness_postmortem.json").write_text(
                json.dumps(dataclasses.asdict(score_result)), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("Post-mortem fitness computation failed: %s", e)

        # Step 6: write manifest
        end_time = time.monotonic()
        manifest = HarvestManifest(
            instance_id=death.instance_id,
            death_trigger=death.trigger,
            death_timestamp=death.timestamp,
            harvest_start_time=start_timestamp,
            harvest_end_time=datetime.now(timezone.utc).isoformat(),
            harvest_duration_seconds=end_time - start_time,
            artifacts=artifacts,
            fitness_score=fitness_score,
            artifact_count=len([a for a in artifacts if a.success]),
            failed_artifacts=len([a for a in artifacts if not a.success]),
        )
        self._manifest_writer.write(manifest, output_dir)

        # Step 7: write GRAVEYARD_HARVEST_COMPLETE
        self._event_log.write_event(
            "GRAVEYARD_HARVEST_COMPLETE",
            0,
            "graveyard",
            {
                "artifact_paths": [a.output for a in artifacts if a.success],
                "harvest_duration_seconds": end_time - start_time,
                "artifact_count": manifest.artifact_count,
            },
        )

        # Step 8: write sentinel file
        sentinel = self._runtime_base / "graveyard" / "harvest_complete"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(
            json.dumps(
                {
                    "instance_id": death.instance_id,
                    "death_timestamp": death.timestamp,
                    "output_dir": str(output_dir),
                    "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )

        # Step 9: return — caller handles process exit
        # Step 10: lifecycle reset — prepare workspace for the next generation
        self._workspace_reset.execute()
