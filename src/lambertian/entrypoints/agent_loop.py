"""Agent loop entrypoint — wires dependencies and starts the turn engine."""

import logging
from pathlib import Path

from lambertian.bootstrap.agent_bootstrap import AgentBootstrap
from lambertian.configuration.loader import load_config
from lambertian.configuration.validator import validate_config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    # Suppress chatty third-party HTTP client logs; only show warnings+
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config_path = Path("config/universe.toml")
    config = load_config(config_path)
    validate_config(config)
    bootstrap = AgentBootstrap(config, config_path)
    bootstrap.run()
