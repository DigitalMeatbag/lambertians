"""Pain monitor main polling loop — IS-8.4.3 exact step order."""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from lambertian.configuration.universe_config import Config
from lambertian.pain_monitor.cgroup_reader import CgroupReader
from lambertian.pain_monitor.death_guard import DeathGuard
from lambertian.pain_monitor.delivery_queue import DeliveryQueue
from lambertian.pain_monitor.event_queue_reader import EventQueueReader
from lambertian.pain_monitor.message_formatter import format_event_message, format_stress_message
from lambertian.pain_monitor.pain_history import PainHistory
from lambertian.pain_monitor.readiness import write_ready_file
from lambertian.pain_monitor.stress_scalar import compute_raw, update_ema
from lambertian.pain_monitor.stress_state_store import StressStateStore
from lambertian.pain_monitor.turn_state_reader import TurnStateReader
from lambertian.contracts.pain_records import StressState

_log = logging.getLogger(__name__)


class PainMonitorService:
    """Runs the IS-8.4.3 polling loop until a death condition fires or shutdown is requested."""

    def __init__(
        self,
        config: Config,
        runtime_pain_root: Path,
        turn_state_path: Path,
    ) -> None:
        self._config = config
        self._runtime_pain_root = runtime_pain_root
        self._turn_state_path = turn_state_path

    def run(self) -> None:
        """Main entry point — initialise, write ready file, then poll."""
        cfg = self._config
        pain_root = self._runtime_pain_root
        pain_root.mkdir(parents=True, exist_ok=True)

        cgroup_reader = CgroupReader()
        stress_store = StressStateStore(pain_root / "stress_state.json")
        death_guard = DeathGuard(cfg, pain_root / "death.json")
        turn_reader = TurnStateReader(self._turn_state_path)
        event_queue_reader = EventQueueReader(
            queue_path=pain_root / "event_queue.jsonl",
            cursor_path=pain_root / "event_queue_cursor.json",
        )
        delivery_queue = DeliveryQueue(pain_root / "delivery_queue.json")
        pain_history = PainHistory(pain_root / "pain_history.jsonl")

        # Recover consecutive_above_death from persisted state if available.
        prior_state = stress_store.read()
        ema_scalar: float = prior_state.scalar if prior_state is not None else 0.0
        consecutive_above_death: int = (
            prior_state.consecutive_above_death_threshold
            if prior_state is not None
            else 0
        )

        write_ready_file(pain_root / "ready")
        _log.info("Pain monitor ready. Entering polling loop.")

        shutdown_requested = False

        def _handle_signal(signum: int, frame: object) -> None:
            nonlocal shutdown_requested
            _log.info("Received signal %d — requesting shutdown.", signum)
            shutdown_requested = True

        signal.signal(signal.SIGTERM, _handle_signal)

        while not shutdown_requested:
            loop_start = time.monotonic()

            try:
                self._poll_cycle(
                    cfg=cfg,
                    cgroup_reader=cgroup_reader,
                    stress_store=stress_store,
                    death_guard=death_guard,
                    turn_reader=turn_reader,
                    event_queue_reader=event_queue_reader,
                    delivery_queue=delivery_queue,
                    pain_history=pain_history,
                    ema_scalar_ref=[ema_scalar],
                    consecutive_above_death_ref=[consecutive_above_death],
                )
                ema_scalar = ema_scalar_ref[0] if (ema_scalar_ref := [ema_scalar]) else ema_scalar
            except SystemExit:
                _log.info("Death condition fired — exiting.")
                return
            except KeyboardInterrupt:
                _log.info("KeyboardInterrupt received — shutting down.")
                return

            elapsed = time.monotonic() - loop_start
            sleep_seconds = max(
                0.0,
                float(cfg.pain.stress.sample_interval_seconds) - elapsed,
            )
            try:
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                _log.info("KeyboardInterrupt during sleep — shutting down.")
                return

        _log.info("Pain monitor shutdown complete.")

    def _poll_cycle(
        self,
        cfg: Config,
        cgroup_reader: CgroupReader,
        stress_store: StressStateStore,
        death_guard: DeathGuard,
        turn_reader: TurnStateReader,
        event_queue_reader: EventQueueReader,
        delivery_queue: DeliveryQueue,
        pain_history: PainHistory,
        ema_scalar_ref: list[float],
        consecutive_above_death_ref: list[int],
    ) -> None:
        """Execute one polling cycle per IS-8.4.3."""
        # Step 1: Read current turn number.
        try:
            current_turn = turn_reader.read_turn_number()
        except OSError as exc:
            _log.warning("Turn state read failed: %s", exc)
            current_turn = 0

        # Step 2: Sample cgroup signals.
        try:
            sample = cgroup_reader.sample()
        except OSError as exc:
            _log.warning("Cgroup sample failed: %s", exc)
            from lambertian.pain_monitor.cgroup_reader import ResourceSample
            sample = ResourceSample(
                cpu_usage_fraction=0.0,
                memory_usage_fraction=0.0,
                cpu_psi_some=None,
                memory_psi_some=None,
            )

        # Step 3: Compute raw composite and EMA.
        raw = compute_raw(sample, cfg.pain.stress)
        prior_ema = ema_scalar_ref[0]
        ema_scalar = update_ema(prior_ema, raw, cfg.pain.stress.ema_alpha)
        ema_scalar_ref[0] = ema_scalar

        # Update consecutive above death counter.
        if ema_scalar >= cfg.pain.stress.death_threshold:
            consecutive_above_death_ref[0] += 1
        else:
            consecutive_above_death_ref[0] = 0
        consecutive_above_death = consecutive_above_death_ref[0]

        # Step 4: Write stress_state.json.
        stress_state = StressState(
            scalar=ema_scalar,
            raw_last=raw,
            cpu_pressure_last=sample.cpu_usage_fraction,
            memory_pressure_last=sample.memory_usage_fraction,
            consecutive_above_death_threshold=consecutive_above_death,
            last_sampled_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            stress_store.write(stress_state)
        except OSError as exc:
            _log.warning("Stress state write failed: %s", exc)

        # Step 5: D4(3) — max age check.
        if death_guard.check_max_age(current_turn):
            raise SystemExit(0)

        # Step 6: D4(1) — sustained stress check.
        if death_guard.check_sustained_stress(ema_scalar, consecutive_above_death):
            raise SystemExit(0)

        # Step 7: Stress interrupt threshold message.
        if ema_scalar >= cfg.pain.stress.interrupt_threshold:
            msg = format_stress_message(ema_scalar, cfg)
            try:
                delivery_queue.append_message(msg)
            except OSError as exc:
                _log.warning("Delivery queue append failed: %s", exc)

        # Step 8: Read new events from event_queue.jsonl since cursor.
        try:
            new_events = event_queue_reader.read_new_events()
            new_offset = event_queue_reader.queue_file_size()
        except OSError as exc:
            _log.warning("Event queue read failed: %s", exc)
            new_events = []
            new_offset = event_queue_reader.current_offset()

        # Step 9: Per-event processing.
        live_events = list(new_events)
        if len(live_events) > cfg.pain.events.queue_max_length:
            # Overflow: sort by submitted_at ascending and drop oldest.
            live_events.sort(key=lambda e: e.submitted_at)
            dropped_events = live_events[: len(live_events) - cfg.pain.events.queue_max_length]
            live_events = live_events[cfg.pain.events.queue_max_length :]
            for dropped in dropped_events:
                try:
                    pain_history.append(dropped, dropped=True)
                except OSError as exc:
                    _log.warning("Pain history append failed (dropped): %s", exc)

        for event in live_events:
            # Step 9a: D4(2) — critical event check.
            if death_guard.check_critical_event(event):
                # Still append to history before exiting.
                try:
                    pain_history.append(event, dropped=False)
                except OSError as exc:
                    _log.warning("Pain history append failed: %s", exc)
                raise SystemExit(0)

            # Step 9b: Append to pain_history.jsonl.
            try:
                pain_history.append(event, dropped=False)
            except OSError as exc:
                _log.warning("Pain history append failed: %s", exc)

            # Step 9c: Deliver if above interrupt threshold and not faded.
            faded = (current_turn - event.turn_number) >= cfg.pain.events.fade_turns
            if event.severity >= cfg.pain.events.interrupt_threshold and not faded:
                msg = format_event_message(event, cfg)
                try:
                    delivery_queue.append_message(msg)
                except OSError as exc:
                    _log.warning("Delivery queue append failed: %s", exc)

        # Step 10: Advance cursor.
        try:
            event_queue_reader.advance_cursor(new_offset)
        except OSError as exc:
            _log.warning("Cursor advance failed: %s", exc)
