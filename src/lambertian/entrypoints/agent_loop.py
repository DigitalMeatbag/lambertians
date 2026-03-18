"""Agent loop entrypoint — wires dependencies and starts the turn engine."""

from pathlib import Path

from lambertian.bootstrap.agent_bootstrap import AgentBootstrap
from lambertian.configuration.loader import load_config
from lambertian.configuration.validator import validate_config


def main() -> None:
    config_path = Path("config/universe.toml")
    config = load_config(config_path)
    validate_config(config)
    bootstrap = AgentBootstrap(config, config_path)
    bootstrap.run()
