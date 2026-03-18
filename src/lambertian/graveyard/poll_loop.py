"""IS-12.2 Graveyard poll loop — waits for death record, then triggers harvest."""
from __future__ import annotations

import time

from lambertian.graveyard.harvest_sequence import HarvestSequence
from lambertian.lifecycle.death_record_reader import DeathRecordReader


class GraveyardPollLoop:
    """IS-12.2. Polls for death record every 2 seconds."""

    def __init__(
        self,
        death_reader: DeathRecordReader,
        harvest_sequence: HarvestSequence,
    ) -> None:
        self._death_reader = death_reader
        self._harvest_sequence = harvest_sequence

    def run(self) -> None:
        while True:
            death = self._death_reader.read()
            if death is not None:
                self._harvest_sequence.execute()
                return
            time.sleep(2)
