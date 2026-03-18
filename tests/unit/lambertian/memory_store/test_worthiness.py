"""Tests for WorthinessChecker. IS-10.5."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from lambertian.memory_store.worthiness import WorthinessChecker

MIN_SCORE = 0.25


@pytest.fixture()
def mock_store() -> MagicMock:
    store = MagicMock()
    store.check_last_written_similarity.return_value = 0.0  # not similar by default
    return store


@pytest.fixture()
def checker(mock_store: MagicMock) -> WorthinessChecker:
    return WorthinessChecker(mock_store, MIN_SCORE)


class TestIsWorthy:
    def test_short_content_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("short", "model_response") is False

    def test_exactly_80_chars_passes_length(
        self, mock_store: MagicMock, checker: WorthinessChecker
    ) -> None:
        content = "x" * 80
        assert checker.is_worthy(content, "model_response") is True

    def test_repetitive_content_not_worthy(self, mock_store: MagicMock) -> None:
        mock_store.check_last_written_similarity.return_value = 0.9
        c = WorthinessChecker(mock_store, MIN_SCORE)
        assert c.is_worthy("x" * 100, "model_response") is False

    def test_similarity_exactly_at_threshold_not_worthy(
        self, mock_store: MagicMock
    ) -> None:
        mock_store.check_last_written_similarity.return_value = MIN_SCORE
        c = WorthinessChecker(mock_store, MIN_SCORE)
        assert c.is_worthy("x" * 100, "model_response") is False

    def test_similarity_below_threshold_worthy(
        self, checker: WorthinessChecker
    ) -> None:
        content = "A" * 100
        assert checker.is_worthy(content, "model_response") is True

    def test_http_status_echo_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("200 OK", "tool_result") is False

    def test_not_found_echo_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("not_found", "tool_result") is False

    def test_none_string_echo_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("None", "tool_result") is False

    def test_null_string_echo_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("null", "tool_result") is False

    def test_empty_content_not_worthy(self, checker: WorthinessChecker) -> None:
        assert checker.is_worthy("   ", "tool_result") is False

    def test_echo_guard_only_applies_to_tool_result(
        self, checker: WorthinessChecker
    ) -> None:
        content = "The server returned status code 200 OK and included a detailed response body with useful information about the requested resource."
        # For model_response, rule 3 doesn't apply
        assert checker.is_worthy(content, "model_response") is True

    def test_good_content_worthy(self, checker: WorthinessChecker) -> None:
        content = "This is a substantial piece of content that demonstrates the system is working correctly and producing meaningful output for episodic storage."
        assert checker.is_worthy(content, "model_response") is True
