"""Tests for InstancePolicy dataclasses and policy_loader resolution."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lambertian.configuration.instance_policy import (
    DEFAULT_ACTION_STEMS,
    DEFAULT_EXPLORATION_TOPICS,
    ImmutablePolicy,
    InstancePolicy,
    MutablePolicy,
)
from lambertian.configuration.policy_loader import (
    _RANGES,
    build_default_policy,
    load_mutable_overrides,
    resolve_policy,
)
from lambertian.configuration.universe_config import PolicyConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config() -> MagicMock:
    """Minimal Config mock with turn and policy sections."""
    config = MagicMock()
    config.turn.max_tool_calls_per_turn = 8
    config.turn.max_pain_messages_per_turn = 3
    config.turn.max_context_events = 32
    config.turn.max_consecutive_noop_turns = 3
    config.turn.max_consecutive_reflection_turns = 5
    config.turn.self_prompt_retry_limit = 2
    config.policy = PolicyConfig(
        response_excerpt_max_chars=500,
        tool_result_summary_max_chars=150,
        working_memory_excerpt_max_chars=400,
        suppression_threshold=3,
        repetition_detection_window=3,
        rolling_context_extraction_count=5,
    )
    return config


# ---------------------------------------------------------------------------
# Dataclass construction
# ---------------------------------------------------------------------------

class TestDataclassConstruction:
    def test_immutable_policy_frozen(self):
        ip = ImmutablePolicy(
            max_tool_calls_per_turn=8, max_pain_messages_per_turn=3,
            max_context_events=32, max_consecutive_noop_turns=3,
            max_consecutive_reflection_turns=5, self_prompt_retry_limit=2,
            noop_min_chars=10,
        )
        with pytest.raises(AttributeError):
            ip.noop_min_chars = 20  # type: ignore[misc]

    def test_mutable_policy_frozen(self):
        mp = MutablePolicy(
            response_excerpt_max_chars=500, tool_result_summary_max_chars=150,
            working_memory_excerpt_max_chars=400, suppression_threshold=3,
            repetition_detection_window=3, rolling_context_extraction_count=5,
            action_stems=DEFAULT_ACTION_STEMS, exploration_topics=DEFAULT_EXPLORATION_TOPICS,
        )
        with pytest.raises(AttributeError):
            mp.suppression_threshold = 5  # type: ignore[misc]

    def test_instance_policy_composes(self):
        ip = ImmutablePolicy(
            max_tool_calls_per_turn=8, max_pain_messages_per_turn=3,
            max_context_events=32, max_consecutive_noop_turns=3,
            max_consecutive_reflection_turns=5, self_prompt_retry_limit=2,
            noop_min_chars=10,
        )
        mp = MutablePolicy(
            response_excerpt_max_chars=500, tool_result_summary_max_chars=150,
            working_memory_excerpt_max_chars=400, suppression_threshold=3,
            repetition_detection_window=3, rolling_context_extraction_count=5,
            action_stems=DEFAULT_ACTION_STEMS, exploration_topics=DEFAULT_EXPLORATION_TOPICS,
        )
        policy = InstancePolicy(immutable=ip, mutable=mp)
        assert policy.immutable.noop_min_chars == 10
        assert policy.mutable.response_excerpt_max_chars == 500


# ---------------------------------------------------------------------------
# build_default_policy
# ---------------------------------------------------------------------------

class TestBuildDefaultPolicy:
    def test_builds_from_config(self):
        config = _make_config()
        policy = build_default_policy(config)
        assert policy.immutable.max_tool_calls_per_turn == 8
        assert policy.immutable.noop_min_chars == 10
        assert policy.mutable.response_excerpt_max_chars == 500
        assert policy.mutable.action_stems == DEFAULT_ACTION_STEMS
        assert policy.mutable.exploration_topics == DEFAULT_EXPLORATION_TOPICS


# ---------------------------------------------------------------------------
# load_mutable_overrides
# ---------------------------------------------------------------------------

class TestLoadMutableOverrides:
    def _defaults(self) -> MutablePolicy:
        return MutablePolicy(
            response_excerpt_max_chars=500, tool_result_summary_max_chars=150,
            working_memory_excerpt_max_chars=400, suppression_threshold=3,
            repetition_detection_window=3, rolling_context_extraction_count=5,
            action_stems=DEFAULT_ACTION_STEMS, exploration_topics=DEFAULT_EXPLORATION_TOPICS,
        )

    def test_missing_file_returns_defaults(self, tmp_path: Path):
        result = load_mutable_overrides(tmp_path / "nonexistent.json", self._defaults())
        assert result == self._defaults()

    def test_valid_override_applied(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps({"suppression_threshold": 5}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result.suppression_threshold == 5
        # Other fields unchanged.
        assert result.response_excerpt_max_chars == 500

    def test_value_clamped_to_range(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        # suppression_threshold range is [2, 10]
        policy_path.write_text(json.dumps({"suppression_threshold": 99}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result.suppression_threshold == 10

    def test_value_clamped_below_minimum(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps({"suppression_threshold": 0}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result.suppression_threshold == 2

    def test_bad_json_returns_defaults(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text("not json{{{")
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result == self._defaults()

    def test_non_dict_root_returns_defaults(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps([1, 2, 3]))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result == self._defaults()

    def test_string_list_override(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps({"action_stems": ["Stem A ", "Stem B "]}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result.action_stems == ("Stem A ", "Stem B ")

    def test_string_list_empty_returns_defaults(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps({"action_stems": []}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert result.action_stems == DEFAULT_ACTION_STEMS

    def test_string_list_max_entries_truncated(self, tmp_path: Path):
        policy_path = tmp_path / "policy.json"
        stems = [f"Stem {i} " for i in range(30)]
        policy_path.write_text(json.dumps({"action_stems": stems}))
        result = load_mutable_overrides(policy_path, self._defaults())
        assert len(result.action_stems) == 20


# ---------------------------------------------------------------------------
# resolve_policy (integration)
# ---------------------------------------------------------------------------

class TestResolvePolicy:
    def test_no_override_file(self, tmp_path: Path):
        config = _make_config()
        policy = resolve_policy(config, tmp_path / "policy.json")
        assert policy.mutable.suppression_threshold == 3

    def test_with_override_file(self, tmp_path: Path):
        config = _make_config()
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps({"repetition_detection_window": 7}))
        policy = resolve_policy(config, policy_path)
        assert policy.mutable.repetition_detection_window == 7
        assert policy.immutable.max_tool_calls_per_turn == 8
