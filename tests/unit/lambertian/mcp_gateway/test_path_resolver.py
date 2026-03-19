"""Unit tests for PathResolver boundary enforcement. IS-7.4."""

from __future__ import annotations

from pathlib import Path

import pytest

from lambertian.mcp_gateway.path_resolver import PathBoundaryViolation, PathResolver


@pytest.fixture()
def resolver(tmp_path: Path) -> PathResolver:
    runtime_base = tmp_path / "runtime"
    config_base = tmp_path / "config"
    # Create the roots so resolve() works on Windows (resolve requires existing path on some systems).
    runtime_base.mkdir()
    config_base.mkdir()
    return PathResolver(runtime_base, config_base)


@pytest.fixture()
def runtime_base(tmp_path: Path) -> Path:
    p = tmp_path / "runtime"
    p.mkdir()
    return p


@pytest.fixture()
def config_base(tmp_path: Path) -> Path:
    p = tmp_path / "config"
    p.mkdir()
    return p


class TestResolveRead:
    def test_memory_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "memory" / "episodic.db"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_event_stream_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "event_stream" / "events.jsonl"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_fitness_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "fitness" / "current.json"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_self_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "self" / "self_model.json"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_pain_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "pain" / "stress.json"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_agent_work_path_permitted_for_read(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "runtime" / "agent-work" / "notes.txt"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_config_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "config" / "universe.toml"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()

    def test_runtime_root_itself_rejected(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "runtime" / "some_unlisted_dir" / "file.txt"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_read(str(target))
    def test_outside_all_roots_rejected(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "secret" / "credentials.txt"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_read(str(target))

    def test_path_traversal_attempt_rejected(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        # Attempt to escape via ..
        target = tmp_path / "runtime" / "memory" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_read(str(target))

    def test_root_dir_itself_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        # The memory root directory itself should be resolvable.
        target = tmp_path / "runtime" / "memory"
        resolved = resolver.resolve_read(str(target))
        assert resolved == target.resolve()


class TestResolveWrite:
    def test_agent_work_path_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "agent-work" / "output.txt"
        resolved = resolver.resolve_write(str(target))
        assert resolved == target.resolve()

    def test_agent_work_subdir_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "agent-work" / "notes" / "draft.txt"
        resolved = resolver.resolve_write(str(target))
        assert resolved == target.resolve()

    def test_memory_path_rejected_for_write(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "runtime" / "memory" / "poisoned.db"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_write(str(target))

    def test_config_path_rejected_for_write(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "config" / "universe.toml"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_write(str(target))

    def test_outside_all_roots_rejected(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "etc" / "crontab"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_write(str(target))


class TestResolveList:
    def test_memory_dir_permitted(self, resolver: PathResolver, tmp_path: Path) -> None:
        target = tmp_path / "runtime" / "memory"
        resolved = resolver.resolve_list(str(target))
        assert resolved == target.resolve()

    def test_runtime_root_permitted_for_list(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        # runtime/ itself is a valid list target for subdirectory discovery.
        target = tmp_path / "runtime"
        resolved = resolver.resolve_list(str(target))
        assert resolved == target.resolve()

    def test_dot_redirects_to_runtime_root(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        # '.' is silently normalized to runtime/ so the model can discover subdirectories.
        resolved = resolver.resolve_list(".")
        assert resolved == (tmp_path / "runtime").resolve()

    def test_bare_slash_redirects_to_runtime_root(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        resolved = resolver.resolve_list("/")
        assert resolved == (tmp_path / "runtime").resolve()

    def test_runtime_root_still_rejected_for_read(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        # runtime/ is list-only — reading a file directly in runtime/ is not permitted.
        target = tmp_path / "runtime" / "unlisted_file.txt"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_read(str(target))

    def test_outside_all_roots_rejected(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "hidden"
        with pytest.raises(PathBoundaryViolation):
            resolver.resolve_list(str(target))


class TestLeadingSlashNormalization:
    """Tests for the leading-slash normalization fallback (container model path correction)."""

    def test_error_message_contains_hint(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        # Boundary violation error should include the path hint.
        with pytest.raises(PathBoundaryViolation, match="Tools work"):
            resolver.resolve_list(str(tmp_path / "hidden"))

    def test_write_boundary_violation_message_contains_hint(
        self, resolver: PathResolver, tmp_path: Path
    ) -> None:
        target = tmp_path / "runtime" / "memory" / "file.txt"
        with pytest.raises(PathBoundaryViolation, match="Tools work"):
            resolver.resolve_write(str(target))

