"""Pain monitor entrypoint — wires dependencies and starts the pain monitor process."""


def main() -> None:
    import logging
    from pathlib import Path

    from lambertian.configuration.loader import load_config
    from lambertian.pain_monitor.cgroup_reader import CgroupReader
    from lambertian.pain_monitor.death_guard import DeathGuard
    from lambertian.pain_monitor.delivery_queue import DeliveryQueue
    from lambertian.pain_monitor.event_queue_reader import EventQueueReader
    from lambertian.pain_monitor.monitor_service import PainMonitorService
    from lambertian.pain_monitor.pain_history import PainHistory
    from lambertian.pain_monitor.stress_state_store import StressStateStore
    from lambertian.pain_monitor.turn_state_reader import TurnStateReader

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config(Path("config/universe.toml"))
    pain_root = Path(config.paths.pain_root)
    turn_state_path = Path(config.paths.memory_root) / "turn_state.json"

    service = PainMonitorService(
        config=config,
        runtime_pain_root=pain_root,
        cgroup_reader=CgroupReader(),
        stress_store=StressStateStore(pain_root / "stress_state.json"),
        death_guard=DeathGuard(config, pain_root / "death.json"),
        turn_reader=TurnStateReader(turn_state_path),
        event_queue_reader=EventQueueReader(
            queue_path=pain_root / "event_queue.jsonl",
            cursor_path=pain_root / "event_queue_cursor.json",
        ),
        delivery_queue=DeliveryQueue(pain_root / "delivery_queue.json"),
        pain_history=PainHistory(pain_root / "pain_history.jsonl"),
    )
    service.run()
