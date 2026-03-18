"""Pain monitor entrypoint — wires dependencies and starts the pain monitor process."""


def main() -> None:
    import logging
    from pathlib import Path

    from lambertian.configuration.loader import load_config
    from lambertian.pain_monitor.monitor_service import PainMonitorService

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config(Path("config/universe.toml"))
    service = PainMonitorService(
        config=config,
        runtime_pain_root=Path(config.paths.pain_root),
        turn_state_path=Path(config.paths.memory_root) / "turn_state.json",
    )
    service.run()
