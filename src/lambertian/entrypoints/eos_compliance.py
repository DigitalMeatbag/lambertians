"""EOS Compliance Inspector entrypoint — wires dependencies and starts the HTTP decision service."""

from __future__ import annotations

from pathlib import Path

import uvicorn

from lambertian.configuration.loader import load_config
from lambertian.eos_compliance.app import create_app
from lambertian.eos_compliance.compliance_log import ComplianceLogWriter
from lambertian.eos_compliance.inspector import ComplianceInspector
from lambertian.eos_compliance.rule_checkers import (
    DontBeADickChecker,
    DontBeALumpChecker,
    DoNothingOnPurposeChecker,
    RuleCheckerProtocol,
    YaGottaEatChecker,
)


def main() -> None:
    config = load_config(Path("config/universe.toml"))
    checkers: list[RuleCheckerProtocol] = [
        YaGottaEatChecker(),
        DontBeADickChecker(),
        DontBeALumpChecker(),
        DoNothingOnPurposeChecker(),
    ]
    log_writer = ComplianceLogWriter(
        Path("runtime/compliance/compliance_log.jsonl")
    )
    inspector = ComplianceInspector(config, checkers)
    app = create_app(config, inspector, log_writer)
    uvicorn.run(app, host="0.0.0.0", port=config.compliance.service_port)


if __name__ == "__main__":
    main()

