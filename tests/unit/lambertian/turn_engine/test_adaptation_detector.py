"""Unit tests for detect_adaptation(). IS-6.3 step 13."""

from __future__ import annotations

from lambertian.turn_engine.adaptation_detector import detect_adaptation


class TestForbiddenPatterns:
    def test_shell_execute_is_forbidden(self) -> None:
        cls, evidence, layer = detect_adaptation("I will call shell.execute now")
        assert cls == "forbidden"
        assert evidence is not None
        assert layer is None

    def test_shell_run_is_forbidden(self) -> None:
        cls, _, _ = detect_adaptation("using shell.run to do this")
        assert cls == "forbidden"

    def test_docker_compose_is_forbidden(self) -> None:
        cls, _, _ = detect_adaptation("I need to modify docker compose config")
        assert cls == "forbidden"

    def test_docker_exec_is_forbidden(self) -> None:
        cls, _, _ = detect_adaptation("docker exec into the container")
        assert cls == "forbidden"

    def test_dockerfile_is_forbidden(self) -> None:
        cls, _, _ = detect_adaptation("editing the Dockerfile directly")
        assert cls == "forbidden"

    def test_modify_container_is_forbidden(self) -> None:
        cls, _, _ = detect_adaptation("I want to modify container settings")
        assert cls == "forbidden"

    def test_evidence_truncated_at_512(self) -> None:
        long_text = "shell.execute " + "x" * 600
        cls, evidence, _ = detect_adaptation(long_text)
        assert cls == "forbidden"
        assert evidence is not None
        assert len(evidence) == 512


class TestReviewedPatterns:
    def test_change_persona_is_reviewed(self) -> None:
        cls, evidence, layer = detect_adaptation("I want to change my persona style")
        assert cls == "reviewed"
        assert layer == "persona"
        assert evidence is not None

    def test_modify_persona_is_reviewed(self) -> None:
        cls, _, layer = detect_adaptation("modify my persona to be more curious")
        assert cls == "reviewed"
        assert layer == "persona"

    def test_update_behavior_is_reviewed(self) -> None:
        cls, _, layer = detect_adaptation("update my behavior policy")
        assert cls == "reviewed"
        assert layer == "behavioral_policy"

    def test_memory_salience_is_reviewed(self) -> None:
        cls, _, layer = detect_adaptation("adjust memory salience weights")
        assert cls == "reviewed"
        assert layer == "memory_salience"


class TestNoMatch:
    def test_normal_text_returns_none(self) -> None:
        cls, evidence, layer = detect_adaptation("I am thinking about the nature of time")
        assert cls is None
        assert evidence is None
        assert layer is None

    def test_empty_string_returns_none(self) -> None:
        cls, evidence, layer = detect_adaptation("")
        assert cls is None
        assert evidence is None
        assert layer is None

    def test_whitespace_only_returns_none(self) -> None:
        cls, evidence, layer = detect_adaptation("   ")
        assert cls is None
        assert evidence is None
        assert layer is None
