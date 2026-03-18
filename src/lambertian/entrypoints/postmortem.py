"""IS-12 Phase 2 — post-mortem viewer CLI entrypoint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lambertian.postmortem.artifact_reader import read_artifact
from lambertian.postmortem.report_renderer import render


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lambertian-postmortem",
        description="View a Lambertian graveyard post-mortem artifact.",
    )
    parser.add_argument(
        "artifact_dir",
        nargs="?",
        default=None,
        help="Path to a graveyard artifact directory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all artifact directories under --root",
    )
    parser.add_argument(
        "--root",
        default="runtime/graveyard",
        metavar="PATH",
        help="Graveyard root (used with --list, default: runtime/graveyard)",
    )
    args = parser.parse_args()

    if args.list:
        _cmd_list(Path(args.root))
    elif args.artifact_dir:
        _cmd_view(Path(args.artifact_dir))
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_list(root: Path) -> None:
    if not root.exists():
        print(f"Graveyard root not found: {root}", file=sys.stderr)
        sys.exit(1)
    dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if not dirs:
        print(f"No artifact directories found under {root}")
        return
    for d in dirs:
        print(d)


def _cmd_view(artifact_dir: Path) -> None:
    if not artifact_dir.exists():
        print(f"Artifact directory not found: {artifact_dir}", file=sys.stderr)
        sys.exit(1)
    if not artifact_dir.is_dir():
        print(f"Not a directory: {artifact_dir}", file=sys.stderr)
        sys.exit(1)
    data = read_artifact(artifact_dir)
    print(render(data))
