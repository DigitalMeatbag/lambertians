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
from dataclasses import dataclass, field
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
    ) -> None:
        self._read_shims = read_shims
        self._list_shims = list_shims
        self._virtual_generators = virtual_generators
        self._config = config

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


# ---------------------------------------------------------------------------
# Virtual file generators
# ---------------------------------------------------------------------------


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
    "self/identity": AliasShim("runtime/agent-work/self/identity.md"),
    "self/status": AliasShim("runtime/agent-work/self/state.md"),
    "self/constitution": AliasShim("runtime/agent-work/self/constitution.md"),
    "self/constitution.md": AliasShim("runtime/agent-work/self/constitution.md"),
    # Memory attractors — model reaches for working memory
    "memory/working": AliasShim("runtime/memory/working.json"),
    "memory/working_memory.txt": AliasShim("runtime/memory/working.json"),
    # Workspace map — model reaches for WORKSPACE.md with bare path
    "WORKSPACE.md": AliasShim("runtime/agent-work/WORKSPACE.md"),
    # Agent-work subdirectory files — common prefix error
    "agent-work/log.txt": AliasShim("runtime/agent-work/log.txt"),
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
    "agent_status": generate_agent_status,
}

# Registry of all known model profiles and their shim maps.
_PROFILE_REGISTRY: dict[str, tuple[dict[str, ShimEntry], dict[str, AliasShim]]] = {
    "qwen2.5:32b": (_QWEN_32B_READ_SHIMS, _QWEN_32B_LIST_SHIMS),
    "qwen2.5:14b": (_QWEN_32B_READ_SHIMS, _QWEN_32B_LIST_SHIMS),
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

    read_shims, list_shims = entry
    _log.info(
        "Loaded semantic shim map for %r: %d read shims, %d list shims",
        profile_name,
        len(read_shims),
        len(list_shims),
    )
    return SemanticShimRegistry(
        read_shims=read_shims,
        list_shims=list_shims,
        virtual_generators=_VIRTUAL_GENERATORS,
        config=config,
    )
