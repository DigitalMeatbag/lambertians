"""Policy resolution — builds InstancePolicy from config + optional runtime overrides.

Resolution chain:
    universe.toml (immutable values + mutable defaults)
        → InstancePolicy with code-level mutable defaults
            → self/policy.json overrides (if present and valid)
                → final InstancePolicy for this turn
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from lambertian.configuration.instance_policy import (
    DEFAULT_ACTION_STEMS,
    DEFAULT_EXPLORATION_TOPICS,
    ImmutablePolicy,
    InstancePolicy,
    MutablePolicy,
)
from lambertian.configuration.universe_config import Config

_log = logging.getLogger(__name__)

# Range constraints for mutable fields.  Values outside these ranges
# are silently clamped to the nearest bound.
_RANGES: dict[str, tuple[int, int]] = {
    "response_excerpt_max_chars": (50, 2000),
    "tool_result_summary_max_chars": (50, 500),
    "working_memory_excerpt_max_chars": (100, 1000),
    "suppression_threshold": (2, 10),
    "repetition_detection_window": (2, 10),
    "rolling_context_extraction_count": (3, 20),
}

_MAX_LIST_ENTRIES = 20


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def build_default_policy(config: Config) -> InstancePolicy:
    """Construct an InstancePolicy entirely from Config + code-level defaults."""
    immutable = ImmutablePolicy(
        max_tool_calls_per_turn=config.turn.max_tool_calls_per_turn,
        max_pain_messages_per_turn=config.turn.max_pain_messages_per_turn,
        max_context_events=config.turn.max_context_events,
        max_consecutive_noop_turns=config.turn.max_consecutive_noop_turns,
        max_consecutive_reflection_turns=config.turn.max_consecutive_reflection_turns,
        self_prompt_retry_limit=config.turn.self_prompt_retry_limit,
        noop_min_chars=10,
    )
    mutable = _default_mutable(config)
    return InstancePolicy(immutable=immutable, mutable=mutable)


def _default_mutable(config: Config) -> MutablePolicy:
    """Build the default MutablePolicy from config.policy + code defaults."""
    return MutablePolicy(
        response_excerpt_max_chars=config.policy.response_excerpt_max_chars,
        tool_result_summary_max_chars=config.policy.tool_result_summary_max_chars,
        working_memory_excerpt_max_chars=config.policy.working_memory_excerpt_max_chars,
        suppression_threshold=config.policy.suppression_threshold,
        repetition_detection_window=config.policy.repetition_detection_window,
        rolling_context_extraction_count=config.policy.rolling_context_extraction_count,
        action_stems=DEFAULT_ACTION_STEMS,
        exploration_topics=DEFAULT_EXPLORATION_TOPICS,
    )


def load_mutable_overrides(
    policy_path: Path, defaults: MutablePolicy
) -> MutablePolicy:
    """Read self/policy.json and merge valid overrides into *defaults*.

    On any failure (missing file, bad JSON, wrong types), returns *defaults*
    unchanged with a warning log.
    """
    if not policy_path.exists():
        return defaults

    try:
        raw: dict[str, Any] = json.loads(policy_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("policy.json unreadable (%s), using defaults", exc)
        return defaults

    if not isinstance(raw, dict):
        _log.warning("policy.json root is not an object, using defaults")
        return defaults

    try:
        return _apply_overrides(raw, defaults)
    except Exception as exc:  # noqa: BLE001 — fallback on any validation failure
        _log.warning("policy.json override failed (%s), using defaults", exc)
        return defaults


def _apply_overrides(raw: dict[str, Any], defaults: MutablePolicy) -> MutablePolicy:
    """Apply validated overrides from parsed JSON onto *defaults*."""

    def _int_field(key: str, fallback: int) -> int:
        val = raw.get(key)
        if val is None:
            return fallback
        ival = int(val)
        lo, hi = _RANGES.get(key, (fallback, fallback))
        return _clamp(ival, lo, hi)

    def _str_list_field(
        key: str, fallback: tuple[str, ...]
    ) -> tuple[str, ...]:
        val = raw.get(key)
        if val is None:
            return fallback
        if not isinstance(val, list):
            return fallback
        cleaned = [str(s) for s in val if isinstance(s, str) and s.strip()]
        if not cleaned:
            return fallback
        return tuple(cleaned[:_MAX_LIST_ENTRIES])

    return MutablePolicy(
        response_excerpt_max_chars=_int_field(
            "response_excerpt_max_chars", defaults.response_excerpt_max_chars
        ),
        tool_result_summary_max_chars=_int_field(
            "tool_result_summary_max_chars", defaults.tool_result_summary_max_chars
        ),
        working_memory_excerpt_max_chars=_int_field(
            "working_memory_excerpt_max_chars",
            defaults.working_memory_excerpt_max_chars,
        ),
        suppression_threshold=_int_field(
            "suppression_threshold", defaults.suppression_threshold
        ),
        repetition_detection_window=_int_field(
            "repetition_detection_window", defaults.repetition_detection_window
        ),
        rolling_context_extraction_count=_int_field(
            "rolling_context_extraction_count",
            defaults.rolling_context_extraction_count,
        ),
        action_stems=_str_list_field("action_stems", defaults.action_stems),
        exploration_topics=_str_list_field(
            "exploration_topics", defaults.exploration_topics
        ),
    )


def resolve_policy(config: Config, policy_path: Path) -> InstancePolicy:
    """Build the final InstancePolicy for this turn.

    Immutable section from config.  Mutable section from defaults,
    optionally overridden by *policy_path* (self/policy.json).
    """
    base = build_default_policy(config)
    mutable = load_mutable_overrides(policy_path, base.mutable)
    return InstancePolicy(immutable=base.immutable, mutable=mutable)
