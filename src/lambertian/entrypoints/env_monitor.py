"""Entrypoint for lambertian-env-monitor — runs natively on Windows (not in Docker)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

_log = logging.getLogger(__name__)


def main() -> None:
    from lambertian.configuration.loader import load_config
    from lambertian.env_monitor.aggregator import EnvStateAggregator
    from lambertian.env_monitor.monitor_service import EnvMonitorService
    from lambertian.env_monitor.sensor import SensorProvider
    from lambertian.env_monitor.sensors.cpu_sensor import CpuSensor
    from lambertian.env_monitor.sensors.gpu_sensor import GpuSensor
    from lambertian.env_monitor.sensors.media_sensor import MediaSensor
    from lambertian.env_monitor.sensors.memory_sensor import MemorySensor
    from lambertian.env_monitor.writer import HostStateWriter

    config_path = Path("config/universe.toml")
    if not config_path.exists():
        _log.error("config/universe.toml not found — run from project root")
        sys.exit(1)

    config = load_config(config_path)
    output_path = Path(config.env_monitor.output_path)
    interval = config.env_monitor.update_interval_seconds

    sensors: list[SensorProvider] = [
        CpuSensor(),
        MemorySensor(),
        GpuSensor(),
        MediaSensor(),
    ]

    aggregator = EnvStateAggregator(sensors)
    writer = HostStateWriter(output_path)
    service = EnvMonitorService(aggregator, writer, interval)

    _log.info("Writing host state to %s every %ds", output_path, interval)
    try:
        service.run()
    except KeyboardInterrupt:
        _log.info("EnvMonitorService stopped by user")


if __name__ == "__main__":
    main()
