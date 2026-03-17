"""D4 death detection — checks three independent death triggers (IS-8.2.5)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from lambertian.configuration.universe_config import Config
from lambertian.contracts.pain_records import DeathRecord, PainEvent

_log = logging.getLogger(__name__)


class DeathGuard:
    """Evaluates D4 death conditions and writes the canonical death record."""

    def __init__(self, config: Config, death_record_path: Path) -> None:
        self._config = config
        self._path = death_record_path

    def check_max_age(self, current_turn: int) -> bool:
        """D4(3): returns True if current_turn >= max_age_turns and death was written."""
        if current_turn >= self._config.universe.max_age_turns:
            self.write_death_record(
                trigger="max_age",
                trigger_value=float(current_turn),
                threshold_used=float(self._config.universe.max_age_turns),
                turn_number=current_turn,
            )
            return True
        return False

    def check_sustained_stress(self, scalar: float, consecutive_count: int) -> bool:
        """D4(1): returns True if scalar >= death_threshold for enough consecutive turns."""
        cfg = self._config.pain.stress
        if scalar >= cfg.death_threshold and consecutive_count >= cfg.death_consecutive_turns:
            self.write_death_record(
                trigger="stress_sustained",
                trigger_value=scalar,
                threshold_used=cfg.death_threshold,
                turn_number=0,
            )
            return True
        return False

    def check_critical_event(self, event: PainEvent) -> bool:
        """D4(2): returns True if event.severity >= critical_threshold."""
        threshold = self._config.pain.events.critical_threshold
        if event.severity >= threshold:
            self.write_death_record(
                trigger="pain_event_critical",
                trigger_value=event.severity,
                threshold_used=threshold,
                turn_number=event.turn_number,
            )
            return True
        return False

    def write_death_record(
        self,
        trigger: str,
        trigger_value: float,
        threshold_used: float,
        turn_number: int,
    ) -> None:
        """Write death.json exactly once — first-declared-cause wins."""
        if self._path.exists():
            return

        record = DeathRecord(
            instance_id=self._config.universe.instance_id,
            trigger=trigger,
            trigger_value=trigger_value,
            threshold_used=threshold_used,
            turn_number=turn_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        data = json.dumps(
            {
                "instance_id": record.instance_id,
                "trigger": record.trigger,
                "trigger_value": record.trigger_value,
                "threshold_used": record.threshold_used,
                "turn_number": record.turn_number,
                "timestamp": record.timestamp,
            }
        )
        tmp = self._path.with_suffix(".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(data)
            os.replace(tmp, self._path)  # atomic on both POSIX and Windows
            _log.info(
                "Death record written: trigger=%s value=%.4f",
                trigger,
                trigger_value,
            )
        except OSError as exc:
            _log.error("Failed to write death record: %s", exc)
