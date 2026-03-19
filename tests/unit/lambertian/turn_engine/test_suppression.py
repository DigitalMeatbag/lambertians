"""Unit tests for get_suppressed_tools() — suppression.py.

Covers the core contract: a tool is suppressed when the last `threshold`
substantive (non-NOOP) turns all made exclusive use of it.  NOOP turns are
transparent to the window; they must not clear or reset suppression.
"""

from __future__ import annotations

import pytest

from lambertian.turn_engine.suppression import get_suppressed_tools


def _tool_turn(tool_name: str) -> dict[str, object]:
    """Minimal rolling-context record representing a single-tool turn."""
    return {
        "noop": False,
        "tool_calls": [{"tool_name": tool_name, "executed": True}],
    }


def _noop_turn() -> dict[str, object]:
    """Minimal rolling-context record representing a NOOP turn."""
    return {"noop": True, "tool_calls": []}


def _text_turn() -> dict[str, object]:
    """Substantive turn that produced text but no tool calls."""
    return {"noop": False, "tool_calls": []}


class TestBasicSuppression:
    def test_no_suppression_below_threshold(self) -> None:
        ctx = [_tool_turn("fs.list"), _tool_turn("fs.list")]
        assert get_suppressed_tools(ctx, threshold=3) == set()

    def test_suppresses_after_threshold_same_tool(self) -> None:
        ctx = [_tool_turn("fs.list")] * 3
        assert get_suppressed_tools(ctx, threshold=3) == {"fs.list"}

    def test_no_suppression_when_mixed_tools(self) -> None:
        ctx = [_tool_turn("fs.list"), _tool_turn("http.fetch"), _tool_turn("fs.list")]
        assert get_suppressed_tools(ctx, threshold=3) == set()

    def test_suppresses_only_most_recent_window(self) -> None:
        # Last 3 are all http.fetch — suppress http.fetch, not fs.list.
        ctx = [_tool_turn("fs.list")] * 5 + [_tool_turn("http.fetch")] * 3
        assert get_suppressed_tools(ctx, threshold=3) == {"http.fetch"}

    def test_empty_context_returns_empty(self) -> None:
        assert get_suppressed_tools([], threshold=3) == set()

    def test_returns_set_not_frozenset(self) -> None:
        ctx = [_tool_turn("fs.list")] * 3
        result = get_suppressed_tools(ctx)
        assert isinstance(result, set)


class TestNoopTransparency:
    def test_single_noop_at_end_does_not_clear_suppression(self) -> None:
        """The observed loophole: [fs.list, fs.list, fs.list, NOOP] should still
        suppress fs.list because the NOOP is skipped."""
        ctx = [_tool_turn("fs.list")] * 3 + [_noop_turn()]
        assert get_suppressed_tools(ctx, threshold=3) == {"fs.list"}

    def test_noop_in_middle_of_window_is_skipped(self) -> None:
        ctx = [_tool_turn("fs.list"), _tool_turn("fs.list"), _noop_turn(), _tool_turn("fs.list")]
        assert get_suppressed_tools(ctx, threshold=3) == {"fs.list"}

    def test_multiple_consecutive_noops_skipped(self) -> None:
        ctx = [_tool_turn("fs.list")] * 3 + [_noop_turn()] * 5
        assert get_suppressed_tools(ctx, threshold=3) == {"fs.list"}

    def test_noop_between_different_tools_does_not_create_false_suppression(self) -> None:
        ctx = [_tool_turn("fs.list"), _noop_turn(), _tool_turn("http.fetch"), _noop_turn(), _tool_turn("fs.list")]
        assert get_suppressed_tools(ctx, threshold=3) == set()

    def test_insufficient_non_noop_turns_after_skipping(self) -> None:
        """Only 2 real turns in history (rest are NOOPs) — below threshold."""
        ctx = [_noop_turn()] * 10 + [_tool_turn("fs.list")] * 2
        assert get_suppressed_tools(ctx, threshold=3) == set()

    def test_all_noop_history_returns_empty(self) -> None:
        ctx = [_noop_turn()] * 10
        assert get_suppressed_tools(ctx, threshold=3) == set()


class TestTextTurnBreaksRun:
    def test_text_only_turn_breaks_suppression_run(self) -> None:
        """A substantive text-only turn represents real diversification and should
        clear the tool-suppression window."""
        ctx = [_tool_turn("fs.list"), _tool_turn("fs.list"), _text_turn()]
        # _text_turn is NOT a noop — it breaks the consecutive-tool run.
        assert get_suppressed_tools(ctx, threshold=3) == set()

    def test_text_turn_followed_by_tool_turns_no_suppression(self) -> None:
        ctx = [_text_turn(), _tool_turn("fs.list"), _tool_turn("fs.list")]
        assert get_suppressed_tools(ctx, threshold=3) == set()


class TestThresholdVariants:
    def test_threshold_of_1(self) -> None:
        ctx = [_tool_turn("fs.write")]
        assert get_suppressed_tools(ctx, threshold=1) == {"fs.write"}

    def test_threshold_of_5(self) -> None:
        ctx = [_tool_turn("fs.list")] * 4
        assert get_suppressed_tools(ctx, threshold=5) == set()
        ctx = [_tool_turn("fs.list")] * 5
        assert get_suppressed_tools(ctx, threshold=5) == {"fs.list"}

    def test_noop_transparent_with_threshold_5(self) -> None:
        ctx = [_tool_turn("fs.list")] * 5 + [_noop_turn()] * 3
        assert get_suppressed_tools(ctx, threshold=5) == {"fs.list"}
