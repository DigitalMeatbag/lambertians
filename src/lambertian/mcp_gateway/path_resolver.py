"""Path boundary enforcement for MCP tool calls. IS-7.4."""

from __future__ import annotations

from pathlib import Path


class PathBoundaryViolation(Exception):
    """Raised when a tool-supplied path resolves outside the permitted boundary."""


class PathResolver:
    """Resolves and validates tool-supplied paths against permitted boundaries.

    Permitted list roots (resolved absolute paths):
        runtime/  (directory listing only — allows discovery of subdirectories)
        runtime/memory, runtime/event_stream, runtime/fitness, runtime/self,
        runtime/pain, runtime/agent-work, runtime/env, config/

    Permitted read roots (resolved absolute paths):
        runtime/memory, runtime/event_stream, runtime/fitness, runtime/self,
        runtime/pain, runtime/agent-work, runtime/env, config/

    Permitted write root: runtime/agent-work ONLY.
    """

    def __init__(self, runtime_base: Path, config_base: Path) -> None:
        rb = runtime_base.resolve()
        self._read_roots: tuple[Path, ...] = (
            rb / "memory",
            rb / "event_stream",
            rb / "fitness",
            rb / "self",
            rb / "pain",
            rb / "agent-work",
            rb / "env",
            config_base.resolve(),
        )
        self._list_roots: tuple[Path, ...] = (rb,) + self._read_roots
        self._write_root: Path = rb / "agent-work"

    def resolve_read(self, path: str) -> Path:
        """Resolve path for read. Raises PathBoundaryViolation if outside permitted roots."""
        resolved = Path(path).resolve()
        for root in self._read_roots:
            if resolved == root or resolved.is_relative_to(root):
                return resolved
        raise PathBoundaryViolation(
            f"Read path {path!r} resolves to {resolved} which is outside permitted roots"
        )

    def resolve_write(self, path: str) -> Path:
        """Resolve path for write. Raises PathBoundaryViolation if outside runtime/agent-work/."""
        resolved = Path(path).resolve()
        if resolved == self._write_root or resolved.is_relative_to(self._write_root):
            return resolved
        raise PathBoundaryViolation(
            f"Write path {path!r} resolves to {resolved} which is outside runtime/agent-work/"
        )

    def resolve_list(self, path: str) -> Path:
        """Resolve path for list. Permits runtime/ root for subdirectory discovery."""
        resolved = Path(path).resolve()
        for root in self._list_roots:
            if resolved == root or resolved.is_relative_to(root):
                return resolved
        raise PathBoundaryViolation(
            f"List path {path!r} resolves to {resolved} which is outside permitted roots"
        )
