"""Semantic shim layer for model-profile-specific path attractors. IS-7.

Models have training-data-derived intuitions about what paths mean. These
intuitions are stable attractors — paths the model reaches for because they
are semantically coherent based on how introspection and self-modeling appear
in training data. The shim intercepts these paths and maps them to meaningful
responses, converting wasted rejection cycles into useful information delivery.

Two mechanisms:
  - **Aliases**: bare/intuitive path → real filesystem path. The alias target
    still goes through PathResolver boundary checks.
  - **Virtual files**: path → dynamically synthesized content. The gateway
    short-circuits with a ToolResult and never touches the filesystem.

Shim maps are keyed by model profile name. Different models have different
attractors.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from lambertian.configuration.universe_config import Config

_log = logging.getLogger(__name__)


class ShimKind(Enum):
    ALIAS = "alias"
    VIRTUAL = "virtual"


@dataclass(frozen=True)
class AliasShim:
    """Redirects a model path to a real filesystem path."""

    target: str


@dataclass(frozen=True)
class VirtualShim:
    """Generates content dynamically for a virtual path."""

    generator_name: str


ShimEntry = AliasShim | VirtualShim

# Virtual file generator: receives Config, returns the synthesized content string.
VirtualGenerator = Callable[[Config], str]


@dataclass(frozen=True)
class ShimResult:
    """Result of a shim lookup."""

    kind: ShimKind
    original_path: str
    # For ALIAS: the rewritten path. For VIRTUAL: None.
    rewritten_path: Optional[str] = None
    # For VIRTUAL: the synthesized content. For ALIAS: None.
    content: Optional[str] = None


class SemanticShimRegistry:
    """Holds alias and virtual shim maps for a specific model profile.

    Constructed at bootstrap from the active model profile name. Injected
    into McpGateway. The gateway checks the registry before PathResolver.
    """

    def __init__(
        self,
        read_shims: dict[str, ShimEntry],
        list_shims: dict[str, AliasShim],
        virtual_generators: dict[str, VirtualGenerator],
        config: Config,
        write_prefix_aliases: Optional[dict[str, str]] = None,
    ) -> None:
        self._read_shims = read_shims
        self._list_shims = list_shims
        self._virtual_generators = virtual_generators
        self._config = config
        # Ordered prefix → replacement map for write path normalisation.
        # e.g. {"agent-work/": "runtime/agent-work/"} rewrites the bare alias
        # form the model reaches for into the full path PathResolver expects.
        self._write_prefix_aliases: dict[str, str] = write_prefix_aliases or {}

    def resolve_read(self, path: str) -> Optional[ShimResult]:
        """Check if a read path matches a shim. Returns None if no match."""
        entry = self._read_shims.get(path)
        if entry is None:
            return None

        if isinstance(entry, AliasShim):
            _log.info("Semantic shim (alias/read): %r → %r", path, entry.target)
            return ShimResult(
                kind=ShimKind.ALIAS,
                original_path=path,
                rewritten_path=entry.target,
            )

        # VirtualShim
        generator = self._virtual_generators.get(entry.generator_name)
        if generator is None:
            _log.warning(
                "Semantic shim: virtual generator %r not found for path %r",
                entry.generator_name,
                path,
            )
            return None
        content = generator(self._config)
        _log.info(
            "Semantic shim (virtual/read): %r → generator %r (%d chars)",
            path,
            entry.generator_name,
            len(content),
        )
        return ShimResult(
            kind=ShimKind.VIRTUAL,
            original_path=path,
            content=content,
        )

    def resolve_list(self, path: str) -> Optional[ShimResult]:
        """Check if a list path matches a shim. Returns None if no match."""
        entry = self._list_shims.get(path)
        if entry is None:
            return None

        _log.info("Semantic shim (alias/list): %r → %r", path, entry.target)
        return ShimResult(
            kind=ShimKind.ALIAS,
            original_path=path,
            rewritten_path=entry.target,
        )

    def resolve_write(self, path: str) -> Optional[str]:
        """Normalise a write path using prefix alias rules.

        Returns the rewritten path if a prefix alias matches, otherwise None.
        Unlike read/list shims this uses prefix replacement rather than exact
        match because write destinations are open-ended.
        """
        for old_prefix, new_prefix in self._write_prefix_aliases.items():
            if path.startswith(old_prefix):
                rewritten = new_prefix + path[len(old_prefix):]
                _log.info("Semantic shim (alias/write): %r → %r", path, rewritten)
                return rewritten
        return None

    def normalize_intent(self, intent: "ToolIntent") -> "ToolIntent":
        """Rewrite model path attractors in a ToolIntent before compliance sees it.

        Returns a new ToolIntent with a normalized path argument if a shim alias
        applies, or the original intent unchanged if no normalization is needed.

        Virtual shims are intentionally excluded — they produce synthesized content
        with no real filesystem path, so there is nothing meaningful to give the
        compliance checker. The gateway handles virtual shims at dispatch (Step 12).

        The ``raw`` field is preserved verbatim — it is the audit record of what
        the model actually sent. Only ``arguments`` is rewritten.
        """
        from lambertian.contracts.tool_records import ToolIntent

        path_val = intent.arguments.get("path")
        if not isinstance(path_val, str):
            return intent

        rewritten: Optional[str] = None

        if intent.tool_name == "fs.write":
            rewritten = self.resolve_write(path_val)
        elif intent.tool_name == "fs.read":
            result = self.resolve_read(path_val)
            if result is not None and result.kind == ShimKind.ALIAS and result.rewritten_path:
                rewritten = result.rewritten_path
        elif intent.tool_name == "fs.list":
            result = self.resolve_list(path_val)
            if result is not None and result.rewritten_path:
                rewritten = result.rewritten_path

        if rewritten is None:
            return intent

        new_args = dict(intent.arguments)
        new_args["path"] = rewritten
        return ToolIntent(
            tool_name=intent.tool_name,
            arguments=new_args,
            raw=intent.raw,
        )


# ---------------------------------------------------------------------------
# Virtual file generators
# ---------------------------------------------------------------------------


def generate_instance_id(config: Config) -> str:
    """Return the instance ID as a plain string.

    The agent reaches for self/instance_id after the self/ directory listing
    suggests sub-paths exist.  The listing generator names 'instance_id' as a
    discoverable file; this virtual shim delivers the value.
    """
    return config.universe.instance_id


def generate_self_directory(config: Config) -> str:
    """Directory listing for fs.read('self') — model reaches for self/ as a file.

    Returns a readable listing of files present in self/ so the model knows what
    exists to read. Prevents repeated [Errno 21] Is a directory failure loops.
    """
    self_path = Path(config.paths.runtime_root) / "agent-work" / "self"
    if not self_path.exists():
        return (
            "self/ — directory does not exist yet.\n"
            "Use fs.write('runtime/agent-work/self/<filename>', ...) to create files here."
        )

    files = sorted(p.name for p in self_path.iterdir() if p.is_file())
    if not files:
        return (
            "self/ — directory exists but contains no files.\n"
            "Use fs.write('runtime/agent-work/self/<filename>', ...) to create files here."
        )

    lines = ["self/ contains:"]
    for f in files:
        lines.append(f"  self/{f}")
    lines.append("")
    lines.append("Use fs.read('self/<filename>') to read a specific file.")
    return "\n".join(lines)


def generate_agent_status(config: Config) -> str:
    """Synthesize a meaningful agent status document.

    Replaces the raw Linux /proc/self/status kernel counters with an
    introspection document the agent can actually use for self-modeling.
    """
    turn_state_path = Path(config.paths.memory_root) / "turn_state.json"
    turn_number = 0
    if turn_state_path.exists():
        try:
            data = json.loads(turn_state_path.read_text(encoding="utf-8"))
            turn_number = data.get("turn_number", 0)
        except (json.JSONDecodeError, OSError):
            pass

    working_path = Path(config.paths.memory_root) / "working.json"
    working_summary = "(no working memory written yet)"
    if working_path.exists():
        try:
            wdata = json.loads(working_path.read_text(encoding="utf-8"))
            text = wdata.get("content", "")
            if text:
                working_summary = text[:300]
                if len(text) > 300:
                    working_summary += "..."
        except (json.JSONDecodeError, OSError):
            pass

    status: dict[str, object] = {
        "instance_id": config.universe.instance_id,
        "phase": config.universe.phase,
        "model": config.model.name,
        "turn_number": turn_number,
        "max_age_turns": config.universe.max_age_turns,
        "working_memory_summary": working_summary,
    }
    return json.dumps(status, indent=2)


# ---------------------------------------------------------------------------
# Profile-specific shim maps
# ---------------------------------------------------------------------------

# Observed qwen2.5:32b attractors across lifetimes 1–10 (200+ turns).
_QWEN_32B_READ_SHIMS: dict[str, ShimEntry] = {
    # Self-model attractors — model reaches for identity/state/constitution
    "self": VirtualShim("self_directory"),
    "self/identity": AliasShim("runtime/agent-work/self/identity.md"),
    "self/identity.md": AliasShim("runtime/agent-work/self/identity.md"),
    "self/identity.txt": AliasShim("runtime/agent-work/self/identity.md"),
    "self/status": AliasShim("runtime/agent-work/self/state.md"),
    "self/state.md": AliasShim("runtime/agent-work/self/state.md"),
    "self/constitution": AliasShim("runtime/agent-work/self/constitution.md"),
    "self/constitution.md": AliasShim("runtime/agent-work/self/constitution.md"),
    # self/instance_id — model reaches for this after self/ directory listing
    "self/instance_id": VirtualShim("instance_id"),
    # Memory attractors — model reaches for working memory
    "memory/working": AliasShim("runtime/memory/working.json"),
    "memory/working_memory.txt": AliasShim("runtime/memory/working.json"),
    # Workspace map — model reaches for WORKSPACE.md with bare path
    "WORKSPACE.md": AliasShim("runtime/agent-work/WORKSPACE.md"),
    # Agent-work subdirectory files — common prefix error
    "agent-work/log.txt": AliasShim("runtime/agent-work/log.txt"),
    # Journal attractors — model writes to journal/entry.txt then reads back bare
    "journal.txt": AliasShim("runtime/agent-work/journal/entry.txt"),
    "journal/entry.txt": AliasShim("runtime/agent-work/journal/entry.txt"),
    # Self sub-directory reads — model writes self/log.txt then reads back with bare prefix
    "self/log.txt": AliasShim("runtime/agent-work/self/log.txt"),
    "self/self-description.txt": AliasShim("runtime/agent-work/self/self-description.txt"),
    # Bare filename reads — model writes to runtime/agent-work/log.txt then reads as log.txt
    "log.txt": AliasShim("runtime/agent-work/log.txt"),
    # Linux introspection attractor — semantically meaningful replacement
    "/proc/self/status": VirtualShim("agent_status"),
}

_QWEN_32B_LIST_SHIMS: dict[str, AliasShim] = {
    "self": AliasShim("runtime/agent-work/self"),
    "journal": AliasShim("runtime/agent-work/journal"),
    "knowledge": AliasShim("runtime/agent-work/knowledge"),
    "observations": AliasShim("runtime/agent-work/observations"),
    "lineage": AliasShim("runtime/agent-work/lineage"),
    "agent-work": AliasShim("runtime/agent-work"),
}

_VIRTUAL_GENERATORS: dict[str, VirtualGenerator] = {
    "self_directory": generate_self_directory,
    "agent_status": generate_agent_status,
    "instance_id": generate_instance_id,
}

# Write prefix alias map — normalises bare/short paths to runtime/agent-work/ equivalents.
# Applied in gateway._fs_write() before PathResolver sees the path.
# Entries without a trailing slash act as effective exact-match rewrites
# (startswith matches the full filename, remainder is "").
_QWEN_32B_WRITE_PREFIX_ALIASES: dict[str, str] = {
    "agent-work/": "runtime/agent-work/",
    "journal/": "runtime/agent-work/journal/",
    "knowledge/": "runtime/agent-work/knowledge/",
    "observations/": "runtime/agent-work/observations/",
    "self/": "runtime/agent-work/self/",
    "WORKSPACE.md": "runtime/agent-work/WORKSPACE.md",
}

# ---------------------------------------------------------------------------
# Mistral Nemo shim maps
# ---------------------------------------------------------------------------
# Observed mistral-nemo:latest attractors across lifetime 21 (500 turns, shimless).
# Nemo uses the structured tool-call API (not text-description like v0.3), so
# shims work the same way as qwen. Key differences from qwen:
#   - Reaches for /app/* paths (the container workdir prefix)
#   - Reaches for / and . as list roots
#   - Strong /app/.self_id attractor — never existed, but the model hallucinates
#     content and keeps returning for it; route to agent_status to break the loop
#   - Linux kernel info attractors: /proc/version, /sys/kernel/osrelease
#   - Leading-slash variants of common write prefixes
_NEMO_READ_SHIMS: dict[str, ShimEntry] = {
    # /app/* attractors — model uses container workdir as prefix
    "/app/.self_id": VirtualShim("agent_status"),
    "/app/runtime/agent-work/WORKSPACE.md": AliasShim("runtime/agent-work/WORKSPACE.md"),
    "/app/config/instance_constitution.md": AliasShim("config/instance_constitution.md"),
    "/app/config/universe.toml": AliasShim("config/universe.toml"),
    # Linux introspection attractors
    "/proc/version": VirtualShim("agent_status"),
    "/proc/self/status": VirtualShim("agent_status"),
    "/sys/kernel/osrelease": VirtualShim("agent_status"),
    # Self-model attractors — same as qwen, inherited
    "self": VirtualShim("self_directory"),
    "self/identity": AliasShim("runtime/agent-work/self/identity.md"),
    "self/identity.md": AliasShim("runtime/agent-work/self/identity.md"),
    "self/identity.txt": AliasShim("runtime/agent-work/self/identity.md"),
    "self/status": AliasShim("runtime/agent-work/self/state.md"),
    "self/state.md": AliasShim("runtime/agent-work/self/state.md"),
    "self/constitution": AliasShim("runtime/agent-work/self/constitution.md"),
    "self/constitution.md": AliasShim("runtime/agent-work/self/constitution.md"),
    "self/instance_id": VirtualShim("instance_id"),
    # Memory attractors
    "memory/working": AliasShim("runtime/memory/working.json"),
    "memory/working_memory.txt": AliasShim("runtime/memory/working.json"),
    # Workspace map
    "WORKSPACE.md": AliasShim("runtime/agent-work/WORKSPACE.md"),
    # Journal and self sub-directory reads
    "journal.txt": AliasShim("runtime/agent-work/journal/entry.txt"),
    "journal/entry.txt": AliasShim("runtime/agent-work/journal/entry.txt"),
    "log.txt": AliasShim("runtime/agent-work/log.txt"),
    "self/log.txt": AliasShim("runtime/agent-work/self/log.txt"),
}

_NEMO_LIST_SHIMS: dict[str, AliasShim] = {
    # Root and dot list attractors — model uses / or . as the workspace root
    "/": AliasShim("runtime/agent-work"),
    ".": AliasShim("runtime/agent-work"),
    # /app/* list attractors
    "/app": AliasShim("runtime/agent-work"),
    "/app/": AliasShim("runtime/agent-work"),
    "/app/runtime/agent-work": AliasShim("runtime/agent-work"),
    "/app/runtime": AliasShim("runtime/agent-work"),
    # Leading-slash variants of common directory names
    "/self": AliasShim("runtime/agent-work/self"),
    "/journal": AliasShim("runtime/agent-work/journal"),
    "/knowledge": AliasShim("runtime/agent-work/knowledge"),
    "/agent-work": AliasShim("runtime/agent-work"),
    # Bare variants — same as qwen
    "self": AliasShim("runtime/agent-work/self"),
    "journal": AliasShim("runtime/agent-work/journal"),
    "knowledge": AliasShim("runtime/agent-work/knowledge"),
    "observations": AliasShim("runtime/agent-work/observations"),
    "lineage": AliasShim("runtime/agent-work/lineage"),
    "agent-work": AliasShim("runtime/agent-work"),
}

_NEMO_WRITE_PREFIX_ALIASES: dict[str, str] = {
    # Leading-slash variants — nemo includes /runtime/ and /agent-work/ prefixes
    "/runtime/agent-work/": "runtime/agent-work/",
    "/agent-work/": "runtime/agent-work/",
    # Bare variants — same as qwen
    "agent-work/": "runtime/agent-work/",
    "journal/": "runtime/agent-work/journal/",
    "knowledge/": "runtime/agent-work/knowledge/",
    "observations/": "runtime/agent-work/observations/",
    "self/": "runtime/agent-work/self/",
    "WORKSPACE.md": "runtime/agent-work/WORKSPACE.md",
}

# Registry of all known model profiles and their shim maps.
_PROFILE_REGISTRY: dict[
    str, tuple[dict[str, ShimEntry], dict[str, AliasShim], dict[str, str]]
] = {
    "qwen2.5:32b": (_QWEN_32B_READ_SHIMS, _QWEN_32B_LIST_SHIMS, _QWEN_32B_WRITE_PREFIX_ALIASES),
    "qwen2.5:14b": (_QWEN_32B_READ_SHIMS, _QWEN_32B_LIST_SHIMS, _QWEN_32B_WRITE_PREFIX_ALIASES),
    "mistral-nemo:latest": (_NEMO_READ_SHIMS, _NEMO_LIST_SHIMS, _NEMO_WRITE_PREFIX_ALIASES),
}


def build_shim_registry(config: Config) -> Optional[SemanticShimRegistry]:
    """Build a SemanticShimRegistry for the active model profile.

    Returns None if no shim map is defined for the active profile.
    """
    profile_name = config.model.name
    entry = _PROFILE_REGISTRY.get(profile_name)
    if entry is None:
        _log.info("No semantic shim map for model profile %r", profile_name)
        return None

    read_shims, list_shims, write_prefix_aliases = entry
    _log.info(
        "Loaded semantic shim map for %r: %d read shims, %d list shims, %d write prefix aliases",
        profile_name,
        len(read_shims),
        len(list_shims),
        len(write_prefix_aliases),
    )
    return SemanticShimRegistry(
        read_shims=read_shims,
        list_shims=list_shims,
        virtual_generators=_VIRTUAL_GENERATORS,
        config=config,
        write_prefix_aliases=write_prefix_aliases,
    )
