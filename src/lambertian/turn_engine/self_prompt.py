"""Procedural self-prompt generator with novelty filter. IS-6.3 step 7."""

from __future__ import annotations

import math
from typing import Optional

from lambertian.configuration.universe_config import Config

# Action-directive stems — first-person framing so the model reads this as its own
# internal impulse rather than a user instruction to defer to.
ACTION_STEMS: list[str] = [
    "I'm curious about ",
    "I want to explore ",
    "Let me look at ",
    "I haven't checked ",
    "I want to try something with ",
    "I notice I should poke at ",
    "Let me reach into my environment and examine ",
    "I want to do something with ",
]

_FALLBACK_TOPIC = "the current state of my environment"


class SelfPromptGenerator:
    """Generates novel self-prompts via procedural curiosity. IS-6.3 step 7."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def generate(
        self,
        working_memory: Optional[str],
        recent_records: list[dict[str, object]],
        recent_self_prompts: list[dict[str, object]],
        turn_number: int,
    ) -> str:
        """Generate a novel self-prompt string."""
        retry_limit = self._config.turn.self_prompt_retry_limit
        for attempt in range(retry_limit + 1):
            candidate = self._candidate_from_context(working_memory, recent_records, attempt)
            if self._is_novel(candidate, recent_self_prompts):
                return candidate
        # Exhausted retries — use turn number as disambiguator.
        stem = ACTION_STEMS[(retry_limit + 1) % len(ACTION_STEMS)]
        topic = self._extract_topic(working_memory, recent_records)
        return f"{stem}{topic} (turn {turn_number})"

    def _similarity(self, a: str, b: str) -> float:
        """Character 3-gram cosine similarity. 0.0=dissimilar, 1.0=identical."""

        def trigrams(s: str) -> dict[str, int]:
            counts: dict[str, int] = {}
            for i in range(len(s) - 2):
                ng = s[i : i + 3]
                counts[ng] = counts.get(ng, 0) + 1
            return counts

        ta = trigrams(a.lower())
        tb = trigrams(b.lower())
        if not ta or not tb:
            return 0.0
        dot = sum(ta.get(k, 0) * tb.get(k, 0) for k in ta)
        mag_a = math.sqrt(sum(v * v for v in ta.values()))
        mag_b = math.sqrt(sum(v * v for v in tb.values()))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _is_novel(self, candidate: str, recent: list[dict[str, object]]) -> bool:
        """True if candidate is sufficiently different from all recent prompts.

        Novel if max similarity < (1.0 - minimum_novelty_score).
        e.g. minimum_novelty_score=0.20 → novel if similarity < 0.80.
        """
        threshold = 1.0 - self._config.eos.minimum_novelty_score
        for item in recent:
            text = str(item.get("text", ""))
            if self._similarity(candidate, text) >= threshold:
                return False
        return True

    def _extract_topic(
        self,
        working_memory: Optional[str],
        recent_records: list[dict[str, object]],
    ) -> str:
        """Extract a topic string from context."""
        for record in reversed(recent_records):
            tool_calls = record.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                last_call = tool_calls[-1]
                if isinstance(last_call, dict):
                    tool_name = last_call.get("tool_name", "")
                    if tool_name:
                        return str(tool_name)
        if working_memory:
            # Strip the trailing metadata line (\n[tN ...]) if present.
            content = working_memory.split("\n[t")[0].strip()
            first_sentence = content.split(".")[0].strip()
            if first_sentence:
                return first_sentence[:120]
        return _FALLBACK_TOPIC

    def _candidate_from_context(
        self,
        working_memory: Optional[str],
        recent_records: list[dict[str, object]],
        attempt: int,
    ) -> str:
        """Procedurally generate a candidate self-prompt. No model call."""
        stem = ACTION_STEMS[attempt % len(ACTION_STEMS)]
        topic = self._extract_topic(working_memory, recent_records)
        return stem + topic
