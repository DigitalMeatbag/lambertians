"""IS-12.3 step 10 — Workspace reset between lifetimes.

Clears the agent's writable workspace at end-of-life and restores a clean scaffold
for the next generation. Called by HarvestSequence after artifacts are collected.

Reset actions (all idempotent):
  1. Remove every entry in runtime/agent-work/ EXCEPT lineage/
  2. Recreate directory stubs: journal/, knowledge/, observations/
  3. Restore WORKSPACE.md from the scaffold template
  4. Reset runtime/memory/turn_state.json to {"turn_number": 0}
  5. Delete within-lifetime memory files (recreated fresh by agent on startup):
       working.json, noop_state.json, recent_self_prompts.json
  6. Remove runtime/pain/death.json so the next instance does not immediately exit
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

_log = logging.getLogger(__name__)

# Subdirectory names preserved across lifetime resets.
_PRESERVED_DIRS: frozenset[str] = frozenset({"lineage"})

# Directory stubs recreated each lifetime.
_SCAFFOLD_DIRS: tuple[str, ...] = ("journal", "knowledge", "observations")

# Within-lifetime memory files deleted on reset (agent recreates on startup if absent).
_EPHEMERAL_MEMORY_FILES: tuple[str, ...] = (
    "working.json",
    "noop_state.json",
    "recent_self_prompts.json",
)


class WorkspaceReset:
    """Resets agent workspace and lifecycle state between generations. IS-12.3 step 10."""

    def __init__(
        self,
        agent_work_dir: Path,
        memory_dir: Path,
        pain_dir: Path,
        workspace_template: Path,
    ) -> None:
        self._agent_work = agent_work_dir
        self._memory = memory_dir
        self._pain = pain_dir
        self._template = workspace_template

    def execute(self) -> None:
        """Run all reset steps. Safe to call multiple times (idempotent)."""
        self._clear_workspace()
        self._recreate_scaffold()
        self._restore_workspace_map()
        self._reset_turn_state()
        self._clear_ephemeral_memory()
        self._remove_death_record()

    # ── Step 1 ────────────────────────────────────────────────────────────────

    def _clear_workspace(self) -> None:
        """Remove all agent-work entries except preserved directories."""
        if not self._agent_work.exists():
            _log.warning("agent-work dir missing, will be created by scaffold step")
            return

        for entry in list(self._agent_work.iterdir()):
            if entry.name in _PRESERVED_DIRS:
                _log.debug("Preserving %s", entry.name)
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
                _log.info("Removed directory: %s", entry.name)
            else:
                entry.unlink()
                _log.info("Removed file: %s", entry.name)

    # ── Step 2 ────────────────────────────────────────────────────────────────

    def _recreate_scaffold(self) -> None:
        """Recreate directory stubs and ensure lineage/ exists."""
        for name in (*_SCAFFOLD_DIRS, "lineage"):
            d = self._agent_work / name
            d.mkdir(parents=True, exist_ok=True)
            _log.debug("Scaffold dir ready: %s", name)

    # ── Step 3 ────────────────────────────────────────────────────────────────

    def _restore_workspace_map(self) -> None:
        """Copy WORKSPACE.md from scaffold template into agent-work/."""
        dest = self._agent_work / "WORKSPACE.md"
        if not self._template.exists():
            _log.error("Workspace template missing: %s", self._template)
            return
        dest.write_text(self._template.read_text(encoding="utf-8"), encoding="utf-8")
        _log.info("Restored WORKSPACE.md from template")

    # ── Step 4 ────────────────────────────────────────────────────────────────

    def _reset_turn_state(self) -> None:
        """Reset turn counter to 0 for the next generation."""
        path = self._memory / "turn_state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"turn_number": 0}), encoding="utf-8")
        _log.info("Turn state reset to 0")

    # ── Step 5 ────────────────────────────────────────────────────────────────

    def _clear_ephemeral_memory(self) -> None:
        """Delete within-lifetime memory files; agent recreates them on startup."""
        for name in _EPHEMERAL_MEMORY_FILES:
            path = self._memory / name
            if path.exists():
                path.unlink()
                _log.info("Deleted ephemeral memory file: %s", name)

    # ── Step 6 ────────────────────────────────────────────────────────────────

    def _remove_death_record(self) -> None:
        """Remove death.json so the next instance does not exit immediately on turn 0."""
        death_json = self._pain / "death.json"
        if death_json.exists():
            death_json.unlink()
            _log.info("Removed death.json")
