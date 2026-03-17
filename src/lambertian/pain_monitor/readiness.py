"""IS-3 readiness signal — writes the empty ready file before entering the polling loop."""

from __future__ import annotations

from pathlib import Path


def write_ready_file(path: Path) -> None:
    """Create the empty ready file in the pain runtime directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
