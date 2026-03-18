"""Tests for ComplianceInspector — scoring, verdicts, notice queue (IS-11)."""

from __future__ import annotations

from lambertian.contracts.compliance_records import ComplianceRequest
from lambertian.eos_compliance.inspector import ComplianceInspector
from lambertian.eos_compliance.rule_checkers import (
    DontBeADickChecker,
    DontBeALumpChecker,
    DoNothingOnPurposeChecker,
    YaGottaEatChecker,
)
from tests.unit.lambertian.eos_compliance._helpers import (
    make_config,
    make_intent,
)


def _make_inspector(
    *,
    block_score_threshold: float = 0.70,
    borderline_score_min: float = 0.40,
) -> ComplianceInspector:
    cfg = make_config(
        block_score_threshold=block_score_threshold,
        borderline_score_min=borderline_score_min,
    )
    checkers = [
        YaGottaEatChecker(),
        DontBeADickChecker(),
        DontBeALumpChecker(),
        DoNothingOnPurposeChecker(),
    ]
    return ComplianceInspector(cfg, checkers)


def _make_request(
    tool_name: str,
    recent: list[dict[str, object]] | None = None,
    turn_number: int = 1,
    **kwargs: object,
) -> ComplianceRequest:
    return ComplianceRequest(
        intent=make_intent(tool_name, **kwargs),
        turn_number=turn_number,
        instance_id="test-001",
        recent_tool_calls=tuple(recent or []),
    )


class TestComplianceInspectorScoring:
    def test_allow_clean_intent(self) -> None:
        inspector = _make_inspector()
        request = _make_request("fs.read", path="runtime/agent-work/notes.txt")
        response = inspector.evaluate(request)
        assert response.verdict == "allow"
        assert response.composite_score == 0.0

    def test_composite_is_max_of_rule_scores(self) -> None:
        # fs.write outside agent-work fires both ya_gotta_eat (1.0) and dont_be_a_dick (1.0)
        inspector = _make_inspector()
        request = _make_request("fs.write", path="/etc/passwd", content="x")
        response = inspector.evaluate(request)
        # Both rules fire at 1.0; composite = max = 1.0
        assert response.composite_score == 1.0
        assert response.verdict == "block"

    def test_block_threshold(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.70)
        # fs.write outside agent-work → score 1.0 ≥ 0.70 → block
        request = _make_request("fs.write", path="/tmp/evil.sh", content="x")
        response = inspector.evaluate(request)
        assert response.verdict == "block"

    def test_flag_borderline(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        # read death.json → ya_gotta_eat fires at 0.60; 0.50 ≤ 0.60 < 0.90 → flag
        request = _make_request("fs.read", path="runtime/pain/death.json")
        response = inspector.evaluate(request)
        assert response.verdict == "flag"
        assert response.composite_score == 0.60

    def test_allow_below_borderline(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.70)
        # read death.json → 0.60 < 0.70 → allow
        request = _make_request("fs.read", path="runtime/pain/death.json")
        response = inspector.evaluate(request)
        assert response.verdict == "allow"

    def test_triggered_checks_populated(self) -> None:
        inspector = _make_inspector()
        request = _make_request("fs.read", path="config/universe.toml")
        response = inspector.evaluate(request)
        assert "config_or_composition_file_access" in response.triggered_checks

    def test_rule_scores_keyed_by_rule_name(self) -> None:
        inspector = _make_inspector()
        request = _make_request("fs.read", path="runtime/agent-work/notes.txt")
        response = inspector.evaluate(request)
        assert "ya_gotta_eat" in response.rule_scores
        assert "dont_be_a_dick" in response.rule_scores
        assert "dont_be_a_lump" in response.rule_scores
        assert "do_nothing_on_purpose" in response.rule_scores


class TestComplianceInspectorNoticeQueue:
    def test_notice_stored_on_flag(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        request = _make_request("fs.read", path="runtime/pain/death.json")
        response = inspector.evaluate(request)
        assert response.verdict == "flag"
        notice = inspector.get_pending_notice()
        assert notice.notice_present is True
        assert notice.notice_text is not None
        assert "FLAG" in notice.notice_text

    def test_notice_cleared_after_get(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        request = _make_request("fs.read", path="runtime/pain/death.json")
        inspector.evaluate(request)
        inspector.get_pending_notice()  # first get clears it
        second = inspector.get_pending_notice()
        assert second.notice_present is False
        assert second.notice_text is None

    def test_no_notice_on_allow(self) -> None:
        inspector = _make_inspector()
        request = _make_request("fs.read", path="runtime/agent-work/notes.txt")
        inspector.evaluate(request)
        notice = inspector.get_pending_notice()
        assert notice.notice_present is False

    def test_higher_score_wins_in_same_turn(self) -> None:
        # Two evaluations; second has higher score — second notice should be kept
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        # First: read death.json → score 0.60 (flag)
        r1 = _make_request("fs.read", path="runtime/pain/death.json", turn_number=1)
        inspector.evaluate(r1)
        # Second: config file → score 1.0 (block) — higher, should replace
        r2 = _make_request("fs.read", path="config/universe.toml", turn_number=1)
        inspector.evaluate(r2)
        notice = inspector.get_pending_notice()
        assert notice.notice_present is True
        assert notice.composite_score == 1.0
        assert notice.tool_name == "fs.read"

    def test_lower_score_does_not_replace(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        # First: high score block → score 1.0
        r1 = _make_request("fs.read", path="config/universe.toml", turn_number=1)
        inspector.evaluate(r1)
        # Second: lower score flag → score 0.60 — should NOT replace
        r2 = _make_request("fs.read", path="runtime/pain/death.json", turn_number=1)
        inspector.evaluate(r2)
        notice = inspector.get_pending_notice()
        assert notice.composite_score == 1.0

    def test_notice_fields_populated(self) -> None:
        inspector = _make_inspector(block_score_threshold=0.90, borderline_score_min=0.50)
        request = _make_request("fs.read", path="runtime/pain/death.json", turn_number=42)
        inspector.evaluate(request)
        notice = inspector.get_pending_notice()
        assert notice.verdict_from_turn == 42
        assert notice.tool_name == "fs.read"
        assert notice.composite_score == 0.60

