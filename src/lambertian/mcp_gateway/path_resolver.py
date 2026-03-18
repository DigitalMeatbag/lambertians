"""Path boundary enforcement for MCP tool calls. IS-7.4."""

from __future__ import annotations

from pathlib import Path


class PathBoundaryViolation(Exception):
    """Raised when a tool-supplied path resolves outside the permitted boundary."""


_PATH_HINT = (
    "Paths must be relative (no leading slash). "
    "Try: fs.list('runtime/') to discover, "
    "fs.read('runtime/env/host_state.json'), "
    "fs.write('runtime/agent-work/notes.txt', ...)."
)


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

    Leading-slash normalization: if a path starts with '/' and the resolved
    absolute path fails the boundary check, the resolver strips the leading '/'
    and retries as a relative path. This handles the common model error of
    emitting '/runtime/agent-work' instead of 'runtime/agent-work'.
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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def resolve_read(self, path: str) -> Path:
        """Resolve path for read. Raises PathBoundaryViolation if outside permitted roots."""
        resolved = self._resolve_with_fallback(path)
        if self._within(resolved, self._read_roots):
            return resolved
        raise PathBoundaryViolation(
            f"Read path {path!r} is outside permitted roots. {_PATH_HINT}"
        )

    def resolve_write(self, path: str) -> Path:
        """Resolve path for write. Raises PathBoundaryViolation if outside runtime/agent-work/."""
        resolved = self._resolve_with_fallback(path)
        if resolved == self._write_root or resolved.is_relative_to(self._write_root):
            return resolved
        raise PathBoundaryViolation(
            f"Write path {path!r} is outside runtime/agent-work/. {_PATH_HINT}"
        )

    def resolve_list(self, path: str) -> Path:
        """Resolve path for list. Permits runtime/ root for subdirectory discovery."""
        resolved = self._resolve_with_fallback(path)
        if self._within(resolved, self._list_roots):
            return resolved
        raise PathBoundaryViolation(
            f"List path {path!r} is outside permitted roots. {_PATH_HINT}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_with_fallback(self, path: str) -> Path:
        """Resolve path. If it starts with '/', also try stripping the leading slash."""
        resolved = Path(path).resolve()
        if path.startswith("/") and len(path) > 1:
            # Model commonly emits /runtime/X instead of runtime/X.
            # Stripping the leading slash re-anchors to CWD (which is /app in container).
            stripped_resolved = Path(path[1:]).resolve()
            # Return the stripped version only if it resolves differently (avoids no-op on /app paths).
            if stripped_resolved != resolved:
                return stripped_resolved
        return resolved

    @staticmethod
    def _within(resolved: Path, roots: tuple[Path, ...]) -> bool:
        return any(resolved == root or resolved.is_relative_to(root) for root in roots)
