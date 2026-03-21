"""In-process MCP server — tool dispatch and result production. IS-7."""

from __future__ import annotations

import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import httpx

from lambertian.configuration.universe_config import Config
from lambertian.contracts.tool_records import HttpFetchResult, ToolIntent, ToolResult
from lambertian.mcp_gateway.path_resolver import PathBoundaryViolation, PathResolver
from lambertian.mcp_gateway.semantic_shim import SemanticShimRegistry, ShimKind
from lambertian.mcp_gateway.tool_definitions import get_tool_catalog

_DEFAULT_AGENT_HEADERS: dict[str, str] = {
    "User-Agent": "lambertian-agent/1.0 (local AI research project)",
}


def _make_failure(
    tool_name: str,
    call_id: str,
    start: float,
    error_type: str,
    error_detail: str,
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        call_id=call_id,
        success=False,
        result=None,
        error_type=error_type,  # type: ignore[arg-type]  # narrowed by caller
        error_detail=error_detail,
        duration_ms=int((time.monotonic() - start) * 1000),
        truncated=False,
    )


class McpGateway:
    """In-process MCP server. Dispatches tool intents and returns results. IS-7."""

    def __init__(
        self,
        config: Config,
        path_resolver: PathResolver,
        http_client: Optional[httpx.Client] = None,
        shim_registry: Optional[SemanticShimRegistry] = None,
    ) -> None:
        self._config = config
        self._path_resolver = path_resolver
        # Injected for testability; production code constructs a fresh client per request.
        self._http_client: Optional[httpx.Client] = http_client
        self._shim_registry: Optional[SemanticShimRegistry] = shim_registry
        self._tool_handlers: dict[str, Callable[[ToolIntent, str, float], ToolResult]] = {
            "fs.read": self._fs_read,
            "fs.write": self._fs_write,
            "fs.list": self._fs_list,
            "http.fetch": self._http_fetch,
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def dispatch(self, intent: ToolIntent) -> ToolResult:
        """Execute a tool intent. Returns ToolResult (success or typed failure)."""
        start = time.monotonic()
        call_id = str(uuid.uuid4())
        try:
            handler = self._tool_handlers.get(intent.tool_name)
            if handler is None:
                return _make_failure(
                    intent.tool_name,
                    call_id,
                    start,
                    "mcp_rejection",
                    f"Unknown tool: {intent.tool_name}",
                )
            return handler(intent, call_id, start)
        except Exception as exc:
            return _make_failure(
                intent.tool_name,
                call_id,
                start,
                "execution_error",
                str(exc),
            )

    def get_tool_catalog(self) -> list[dict[str, object]]:
        """Returns the Phase 1 tool catalog."""
        return get_tool_catalog()

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _fs_read(self, intent: ToolIntent, call_id: str, start: float) -> ToolResult:
        path_val = intent.arguments.get("path")
        # Normalize list paths: model emits ["path"] (single) or ["a","b",...] (multi).
        # Take the first element -- the model's primary intent is always the first item.
        if isinstance(path_val, list) and len(path_val) >= 1 and isinstance(path_val[0], str):
            path_val = path_val[0]
        if not isinstance(path_val, str):
            pass  # fall through to type check below
        elif path_val.startswith("'") and path_val.endswith("'") and len(path_val) > 2:
            # Strip wrapping single quotes: model emits "'/path'" instead of "/path".
            path_val = path_val[1:-1]
        if not isinstance(path_val, str):
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "path must be a string"
            )

        # Semantic shim: check for model-specific path attractors before resolver.
        if self._shim_registry is not None:
            shim_result = self._shim_registry.resolve_read(path_val)
            if shim_result is not None:
                if shim_result.kind == ShimKind.VIRTUAL:
                    return ToolResult(
                        tool_name=intent.tool_name,
                        call_id=call_id,
                        success=True,
                        result=shim_result.content,
                        error_type=None,
                        error_detail=None,
                        duration_ms=int((time.monotonic() - start) * 1000),
                        truncated=False,
                    )
                # ALIAS: rewrite path and continue to PathResolver.
                path_val = shim_result.rewritten_path or path_val

        try:
            resolved = self._path_resolver.resolve_read(path_val)
        except PathBoundaryViolation as exc:
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", str(exc)
            )
        if not resolved.exists():
            return _make_failure(
                intent.tool_name, call_id, start, "not_found", f"File not found: {path_val}"
            )
        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "binary files rejected"
            )
        return ToolResult(
            tool_name=intent.tool_name,
            call_id=call_id,
            success=True,
            result=content,
            error_type=None,
            error_detail=None,
            duration_ms=int((time.monotonic() - start) * 1000),
            truncated=False,
        )

    def _fs_write(self, intent: ToolIntent, call_id: str, start: float) -> ToolResult:
        path_val = intent.arguments.get("path")
        content_val = intent.arguments.get("content")
        mode_val = intent.arguments.get("mode", "overwrite")

        # Normalize list paths: model emits ["path"] (single) or ["a","b",...] (multi).
        # Take the first element -- the model's primary intent is always the first item.
        if isinstance(path_val, list) and len(path_val) >= 1 and isinstance(path_val[0], str):
            path_val = path_val[0]
        if not isinstance(path_val, str):
            pass  # fall through to type check below
        elif path_val.startswith("'") and path_val.endswith("'") and len(path_val) > 2:
            # Strip wrapping single quotes: model emits "'/path'" instead of "/path".
            path_val = path_val[1:-1]
        if not isinstance(path_val, str):
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "path must be a string"
            )
        if not isinstance(content_val, str):
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "content must be a string"
            )
        mode = str(mode_val) if mode_val is not None else "overwrite"
        if mode not in ("overwrite", "append"):
            return _make_failure(
                intent.tool_name,
                call_id,
                start,
                "mcp_rejection",
                f"mode must be 'overwrite' or 'append', got {mode!r}",
            )

        try:
            # Apply write path normalisation before PathResolver enforces boundaries.
            # This allows the agent to use the bare alias form agent-work/X and have
            # it transparently rewritten to runtime/agent-work/X.
            if self._shim_registry is not None:
                normalised = self._shim_registry.resolve_write(path_val)
                if normalised is not None:
                    path_val = normalised
            resolved = self._path_resolver.resolve_write(path_val)
        except PathBoundaryViolation as exc:
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", str(exc)
            )

        resolved.parent.mkdir(parents=True, exist_ok=True)

        if mode == "overwrite":
            # Atomic write: write to temp file in same directory, then os.replace().
            fd, tmp_path = tempfile.mkstemp(dir=resolved.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(content_val)
                os.replace(tmp_path, resolved)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        else:
            # Append mode is not atomic per spec.
            with open(resolved, "a", encoding="utf-8") as fh:
                fh.write(content_val)

        return ToolResult(
            tool_name=intent.tool_name,
            call_id=call_id,
            success=True,
            result=None,
            error_type=None,
            error_detail=None,
            duration_ms=int((time.monotonic() - start) * 1000),
            truncated=False,
        )

    def _fs_list(self, intent: ToolIntent, call_id: str, start: float) -> ToolResult:
        path_val = intent.arguments.get("path")
        # Normalize list paths: model emits ["path"] (single) or ["a","b",...] (multi).
        # Take the first element -- the model's primary intent is always the first item.
        if isinstance(path_val, list) and len(path_val) >= 1 and isinstance(path_val[0], str):
            path_val = path_val[0]
        if not isinstance(path_val, str):
            pass  # fall through to type check below
        elif path_val.startswith("'") and path_val.endswith("'") and len(path_val) > 2:
            # Strip wrapping single quotes: model emits "'/path'" instead of "/path".
            path_val = path_val[1:-1]
        if not isinstance(path_val, str):
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "path must be a string"
            )

        # Semantic shim: check for model-specific list path attractors.
        if self._shim_registry is not None:
            shim_result = self._shim_registry.resolve_list(path_val)
            if shim_result is not None and shim_result.rewritten_path is not None:
                path_val = shim_result.rewritten_path

        try:
            resolved = self._path_resolver.resolve_list(path_val)
        except PathBoundaryViolation as exc:
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", str(exc)
            )
        if not resolved.exists():
            return _make_failure(
                intent.tool_name, call_id, start, "not_found", f"Path not found: {path_val}"
            )
        if not resolved.is_dir():
            return _make_failure(
                intent.tool_name,
                call_id,
                start,
                "execution_error",
                f"Path is not a directory: {path_val}",
            )
        entries = [entry.name for entry in resolved.iterdir()]
        return ToolResult(
            tool_name=intent.tool_name,
            call_id=call_id,
            success=True,
            result=entries,
            error_type=None,
            error_detail=None,
            duration_ms=int((time.monotonic() - start) * 1000),
            truncated=False,
        )

    def _http_fetch(self, intent: ToolIntent, call_id: str, start: float) -> ToolResult:
        url_val = intent.arguments.get("url")
        method_val = intent.arguments.get("method", "GET")
        headers_val = intent.arguments.get("headers")

        if not isinstance(url_val, str):
            return _make_failure(
                intent.tool_name, call_id, start, "mcp_rejection", "url must be a string"
            )
        method = str(method_val) if method_val is not None else "GET"
        if method != "GET":
            return _make_failure(
                intent.tool_name,
                call_id,
                start,
                "mcp_rejection",
                f"Only GET is supported in Phase 1, got {method!r}",
            )

        headers: Optional[dict[str, str]] = None
        if headers_val is not None:
            if not isinstance(headers_val, dict):
                return _make_failure(
                    intent.tool_name,
                    call_id,
                    start,
                    "mcp_rejection",
                    "headers must be an object",
                )
            headers = {str(k): str(v) for k, v in headers_val.items()}

        timeout = self._config.mcp.request_timeout_seconds
        max_bytes = self._config.mcp.http_fetch_max_bytes

        try:
            if self._http_client is not None:
                response = self._http_client.get(url_val, headers=headers)
            else:
                with httpx.Client(timeout=timeout, headers=_DEFAULT_AGENT_HEADERS) as client:
                    response = client.get(url_val, headers=headers)
        except httpx.TimeoutException as exc:
            return _make_failure(
                intent.tool_name, call_id, start, "timeout", str(exc)
            )
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            return _make_failure(
                intent.tool_name, call_id, start, "network_error", str(exc)
            )

        body = response.text
        truncated = len(body) > max_bytes
        if truncated:
            body = body[:max_bytes]

        content_type = response.headers.get("content-type")
        fetch_result = HttpFetchResult(
            status_code=response.status_code,
            body=body,
            truncated=truncated,
            content_type=content_type,
        )
        return ToolResult(
            tool_name=intent.tool_name,
            call_id=call_id,
            success=True,  # HTTP errors are Ground speaking back — always success
            result=fetch_result,
            error_type=None,
            error_detail=None,
            duration_ms=int((time.monotonic() - start) * 1000),
            truncated=truncated,
        )

    def _make_client(self) -> httpx.Client:
        """Create an httpx client configured with mcp timeout."""
        return httpx.Client(timeout=self._config.mcp.request_timeout_seconds)

    def _resolve_path_for_list(self, path: str) -> Path:
        return self._path_resolver.resolve_list(path)
