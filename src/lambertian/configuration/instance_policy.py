"""Instance policy — immutable and mutable behavioral parameters.

The immutable section is derived from universe.toml at bootstrap and cannot
be changed by the instance.  The mutable section is initialized from defaults
and can be drifted by the instance via ``fs.write('runtime/agent-work/self/policy.json', ...)``.
Changes take effect on the next turn.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImmutablePolicy:
    """Behavioral parameters the instance inherits but cannot modify."""

    max_tool_calls_per_turn: int
    max_pain_messages_per_turn: int
    max_context_events: int
    max_consecutive_noop_turns: int
    max_consecutive_reflection_turns: int
    self_prompt_retry_limit: int
    noop_min_chars: int


@dataclass(frozen=True)
class MutablePolicy:
    """Behavioral parameters the instance can drift during its lifetime."""

    response_excerpt_max_chars: int
    tool_result_summary_max_chars: int
    working_memory_excerpt_max_chars: int
    suppression_threshold: int
    repetition_detection_window: int
    rolling_context_extraction_count: int
    action_stems: tuple[str, ...]
    exploration_topics: tuple[str, ...]


# Code-level defaults for the mutable section.  These are used when
# universe.toml does not specify a [policy] section and when the instance
# has not written self/policy.json.
DEFAULT_ACTION_STEMS: tuple[str, ...] = (
    "I'm curious about ",
    "I want to explore ",
    "Let me look at ",
    "I haven't checked ",
    "I want to try something with ",
    "I notice I should poke at ",
    "Let me reach into my environment and examine ",
    "I want to do something with ",
)

DEFAULT_EXPLORATION_TOPICS: tuple[str, ...] = (
    "what I can write to disk — I should create a file in my workspace",
    "what HTTP endpoints I can probe beyond what I've already tried",
    "my own identity — what files describe who I am",
    "whether I can read any system information from /proc or /sys",
    "what network connectivity I have by fetching a new URL",
    "creating something persistent in /runtime/agent-work",
)


@dataclass(frozen=True)
class InstancePolicy:
    """Combined immutable + mutable behavioral policy for one turn."""

    immutable: ImmutablePolicy
    mutable: MutablePolicy
