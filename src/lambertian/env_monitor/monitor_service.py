"""EnvMonitorService — collect → write → sleep loop."""

from __future__ import annotations

import logging
import time

from lambertian.env_monitor.aggregator import EnvStateAggregator
from lambertian.env_monitor.writer import HostStateWriter

_log = logging.getLogger(__name__)


class EnvMonitorService:
    """Runs the collect/write loop at a fixed interval until interrupted."""

    def __init__(
        self,
        aggregator: EnvStateAggregator,
        writer: HostStateWriter,
        interval_seconds: int,
    ) -> None:
        self._aggregator = aggregator
        self._writer = writer
        self._interval = interval_seconds

    def run(self) -> None:
        """Loop forever: collect all sensors, write snapshot, sleep. Ctrl-C exits cleanly."""
        _log.info("EnvMonitorService starting — interval=%ds", self._interval)
        while True:
            try:
                snapshot = self._aggregator.collect_all()
                self._writer.write(snapshot)
            except Exception as exc:
                _log.error("Cycle error (continuing): %s", exc)
            time.sleep(self._interval)
