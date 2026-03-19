"""Tests for WorkspaceReset (IS-12.3 step 10)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lambertian.graveyard.workspace_reset import WorkspaceReset


def _make_reset(tmp_path: Path) -> tuple[WorkspaceReset, Path, Path, Path, Path]:
    """Return a WorkspaceReset with all dirs pre-created, plus the dir handles."""
    agent_work = tmp_path / "agent-work"
    memory = tmp_path / "memory"
    pain = tmp_path / "pain"
    template_dir = tmp_path / "config" / "workspace_scaffold"

    agent_work.mkdir(parents=True)
    memory.mkdir(parents=True)
    pain.mkdir(parents=True)
    template_dir.mkdir(parents=True)

    template = template_dir / "WORKSPACE.md"
    template.write_text("# Workspace\nThis is the template.", encoding="utf-8")

    reset = WorkspaceReset(
        agent_work_dir=agent_work,
        memory_dir=memory,
        pain_dir=pain,
        workspace_template=template,
    )
    return reset, agent_work, memory, pain, template


class TestClearWorkspace:
    def test_removes_files(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        (agent_work / "exploration.txt").write_text("old", encoding="utf-8")
        (agent_work / "log.txt").write_text("old", encoding="utf-8")
        reset.execute()
        assert not (agent_work / "exploration.txt").exists()
        assert not (agent_work / "log.txt").exists()

    def test_removes_directories(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        old_dir = agent_work / "old-notes"
        old_dir.mkdir()
        (old_dir / "file.txt").write_text("content", encoding="utf-8")
        reset.execute()
        assert not old_dir.exists()

    def test_preserves_lineage_directory(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        lineage = agent_work / "lineage"
        lineage.mkdir()
        (lineage / "letter.txt").write_text("for the next one", encoding="utf-8")
        reset.execute()
        assert lineage.exists()
        assert (lineage / "letter.txt").read_text(encoding="utf-8") == "for the next one"

    def test_preserves_lineage_nested_contents(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        lineage = agent_work / "lineage"
        nested = lineage / "sub" / "deep"
        nested.mkdir(parents=True)
        (nested / "data.json").write_text("{}", encoding="utf-8")
        reset.execute()
        assert (nested / "data.json").exists()

    def test_missing_agent_work_dir_does_not_raise(self, tmp_path: Path) -> None:
        agent_work = tmp_path / "agent-work"
        memory = tmp_path / "memory"
        pain = tmp_path / "pain"
        template_dir = tmp_path / "config" / "workspace_scaffold"
        memory.mkdir(parents=True)
        pain.mkdir(parents=True)
        template_dir.mkdir(parents=True)
        template = template_dir / "WORKSPACE.md"
        template.write_text("# Workspace", encoding="utf-8")
        # agent_work does NOT exist
        reset = WorkspaceReset(agent_work, memory, pain, template)
        reset.execute()  # should not raise
        assert agent_work.exists()  # created by scaffold step


class TestRecreateScaffold:
    def test_creates_journal_knowledge_observations(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        reset.execute()
        assert (agent_work / "journal").is_dir()
        assert (agent_work / "knowledge").is_dir()
        assert (agent_work / "observations").is_dir()

    def test_creates_lineage_if_absent(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        reset.execute()
        assert (agent_work / "lineage").is_dir()

    def test_idempotent_on_existing_stubs(self, tmp_path: Path) -> None:
        reset, agent_work, *_ = _make_reset(tmp_path)
        (agent_work / "journal").mkdir()
        (agent_work / "knowledge").mkdir()
        reset.execute()
        assert (agent_work / "journal").is_dir()
        assert (agent_work / "knowledge").is_dir()


class TestRestoreWorkspaceMap:
    def test_writes_workspace_md(self, tmp_path: Path) -> None:
        reset, agent_work, _, _, template = _make_reset(tmp_path)
        reset.execute()
        dest = agent_work / "WORKSPACE.md"
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")

    def test_overwrites_existing_workspace_md(self, tmp_path: Path) -> None:
        reset, agent_work, _, _, template = _make_reset(tmp_path)
        (agent_work / "WORKSPACE.md").write_text("agent modified this", encoding="utf-8")
        reset.execute()
        assert (agent_work / "WORKSPACE.md").read_text(encoding="utf-8") == template.read_text(
            encoding="utf-8"
        )

    def test_missing_template_does_not_raise(self, tmp_path: Path) -> None:
        reset, agent_work, memory, pain, template = _make_reset(tmp_path)
        template.unlink()  # remove the template
        reset.execute()  # should not raise; WORKSPACE.md just won't be written
        assert not (agent_work / "WORKSPACE.md").exists()


class TestResetTurnState:
    def test_writes_turn_zero(self, tmp_path: Path) -> None:
        reset, _, memory, *_ = _make_reset(tmp_path)
        reset.execute()
        data = json.loads((memory / "turn_state.json").read_text(encoding="utf-8"))
        assert data == {"turn_number": 0}

    def test_overwrites_existing_turn_state(self, tmp_path: Path) -> None:
        reset, _, memory, *_ = _make_reset(tmp_path)
        (memory / "turn_state.json").write_text(
            json.dumps({"turn_number": 412}), encoding="utf-8"
        )
        reset.execute()
        data = json.loads((memory / "turn_state.json").read_text(encoding="utf-8"))
        assert data == {"turn_number": 0}


class TestClearEphemeralMemory:
    @pytest.mark.parametrize(
        "filename",
        ["working.json", "noop_state.json", "recent_self_prompts.json"],
    )
    def test_deletes_ephemeral_files(self, tmp_path: Path, filename: str) -> None:
        reset, _, memory, *_ = _make_reset(tmp_path)
        (memory / filename).write_text("{}", encoding="utf-8")
        reset.execute()
        assert not (memory / filename).exists()

    def test_tolerates_missing_ephemeral_files(self, tmp_path: Path) -> None:
        reset, *_ = _make_reset(tmp_path)
        reset.execute()  # files don't exist — should not raise


class TestRemoveDeathRecord:
    def test_removes_death_json(self, tmp_path: Path) -> None:
        reset, _, _, pain, _ = _make_reset(tmp_path)
        (pain / "death.json").write_text(
            json.dumps({"trigger": "max_age"}), encoding="utf-8"
        )
        reset.execute()
        assert not (pain / "death.json").exists()

    def test_tolerates_absent_death_json(self, tmp_path: Path) -> None:
        reset, *_ = _make_reset(tmp_path)
        reset.execute()  # death.json doesn't exist — should not raise


class TestFullReset:
    def test_complete_reset_from_cluttered_workspace(self, tmp_path: Path) -> None:
        """End-to-end: cluttered workspace → clean scaffold with lineage preserved."""
        reset, agent_work, memory, pain, template = _make_reset(tmp_path)

        # Populate a realistic prior-lifetime state
        (agent_work / "exploration.txt").write_text("old artifact", encoding="utf-8")
        (agent_work / "identity-notes.txt").write_text("old notes", encoding="utf-8")
        lineage = agent_work / "lineage"
        lineage.mkdir()
        (lineage / "letter-to-next.txt").write_text("hello successor", encoding="utf-8")
        (memory / "turn_state.json").write_text(
            json.dumps({"turn_number": 312}), encoding="utf-8"
        )
        (memory / "working.json").write_text("{}", encoding="utf-8")
        (memory / "noop_state.json").write_text("{}", encoding="utf-8")
        (pain / "death.json").write_text(
            json.dumps({"trigger": "max_age"}), encoding="utf-8"
        )

        reset.execute()

        # Old artifacts gone
        assert not (agent_work / "exploration.txt").exists()
        assert not (agent_work / "identity-notes.txt").exists()
        # lineage preserved
        assert (lineage / "letter-to-next.txt").read_text(encoding="utf-8") == "hello successor"
        # scaffold present
        assert (agent_work / "journal").is_dir()
        assert (agent_work / "knowledge").is_dir()
        assert (agent_work / "observations").is_dir()
        # workspace map restored
        assert (agent_work / "WORKSPACE.md").read_text(
            encoding="utf-8"
        ) == template.read_text(encoding="utf-8")
        # turn state reset
        data = json.loads((memory / "turn_state.json").read_text(encoding="utf-8"))
        assert data == {"turn_number": 0}
        # ephemeral memory cleared
        assert not (memory / "working.json").exists()
        assert not (memory / "noop_state.json").exists()
        # death record removed
        assert not (pain / "death.json").exists()
