"""IS-12.2 Graveyard poll loop — waits for death record, then triggers harvest."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from lambertian.contracts.pain_records import DeathRecord
from lambertian.graveyard.harvest_sequence import HarvestSequence
from lambertian.lifecycle.death_record_reader import DeathRecordReader

_log = logging.getLogger(__name__)


class GraveyardPollLoop:
    """IS-12.2. Polls for death record every 2 seconds. Keeps running after harvest."""

    def __init__(
        self,
        death_reader: DeathRecordReader,
        harvest_sequence: HarvestSequence,
        sentinel_path: Path,
    ) -> None:
        self._death_reader = death_reader
        self._harvest_sequence = harvest_sequence
        self._sentinel_path = sentinel_path

    def run(self) -> None:
        while True:
            death = self._death_reader.read()
            if death is not None:
                if self._already_harvested(death):
                    time.sleep(2)
                    continue
                self._harvest_sequence.execute()
            else:
                time.sleep(2)

    def _already_harvested(self, death: DeathRecord) -> bool:
        """Return True if the sentinel indicates this exact death was already harvested."""
        if not self._sentinel_path.exists():
            return False
        try:
            saved = json.loads(self._sentinel_path.read_text(encoding="utf-8"))
            return (
                saved.get("instance_id") == death.instance_id
                and saved.get("death_timestamp") == death.timestamp
            )
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning("Could not read harvest sentinel: %s", exc)
            return False
