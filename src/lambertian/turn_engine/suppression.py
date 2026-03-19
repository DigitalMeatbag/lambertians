"""Tool suppression evaluator for the turn engine.

Determines which tools, if any, should be suppressed for the current turn
based on the recent turn history.  A tool is suppressed when the last
``threshold`` *substantive* (non-NOOP) turns all made exclusive use of that
same single tool.

NOOP turns (``record["noop"] is True``) are transparent to the suppression
window: they do not break an active suppression run or reset it.  This
prevents the agent from exploiting a silent NOOP to escape suppression
pressure and immediately resume a suppressed tool.

A non-NOOP turn that produced no tool calls (e.g. a text-only response)
*does* legitimately break the suppression run, because the agent genuinely
diversified its output.

**Path-sensitive suppression for write tools:**
For tools in ``_PATH_SENSITIVE_TOOLS`` (currently ``fs.write``), simple
tool-name repetition is not sufficient to trigger suppression.  The last
``threshold`` calls must also have targeted the *same file path*.  Calling
``fs.write`` on different files is genuine multi-file exploration and is not
suppressed.  If the path cannot be determined (missing or malformed
``intent_raw``), the safe fallback is to suppress.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Optional

# Write tools use path-aware suppression: only suppressed when the same
# destination path is repeated, not merely the same tool name.
_PATH_SENSITIVE_TOOLS: frozenset[str] = frozenset({"fs.write"})


def _extract_tool_path(tc: dict[str, object]) -> Optional[str]:
    """Return the ``path`` argument from a serialised ToolCallRecord, or None.

    Parses ``intent_raw`` (a JSON string of the Ollama function-call object:
    ``{"function": {"name": "...", "arguments": {"path": "...", ...}}}``) to
    extract the path the tool was directed at.  Returns ``None`` if the record
    is missing ``intent_raw``, if the JSON is malformed, or if no ``path``
    argument is present.
    """
    raw = tc.get("intent_raw")
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
        args = parsed.get("function", {}).get("arguments", {})
        path = args.get("path")
        return str(path) if path is not None else None
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None


def get_suppressed_tools(
    rolling_context: Sequence[dict[str, object]],
    threshold: int = 3,
) -> set[str]:
    """Return tool names that should be suppressed this turn.

    If the last ``threshold`` substantive (non-NOOP) turns all called exactly
    the same single tool and nothing else, that tool is returned so the caller
    can remove it from the function-calling schema for one turn.

    For path-sensitive tools (``fs.write``), suppression additionally requires
    that all ``threshold`` calls targeted the *same file path*.  Calls spread
    across different paths are genuine exploration and are not suppressed.

    NOOP turns are skipped when scanning the window; there is no upper bound
    on how many NOOPs may be skipped.  If there are fewer than ``threshold``
    substantive turns in the entire history, no suppression is applied.

    Args:
        rolling_context: Most-recent-last sequence of serialised
            ``TurnRecord`` dicts (as produced by ``dataclasses.asdict``).
        threshold: Number of consecutive same-tool turns required to trigger
            suppression.

    Returns:
        A set containing the single tool name to suppress, or an empty set
        when no suppression is warranted.
    """
    if len(rolling_context) < threshold:
        return set()

    # Walk from newest to oldest, collecting substantive (non-NOOP) records.
    non_noop: list[dict[str, object]] = []
    for record in reversed(rolling_context):
        if record.get("noop"):
            # NOOP turns are transparent — skip without breaking the window.
            continue
        non_noop.append(record)
        if len(non_noop) >= threshold:
            break

    if len(non_noop) < threshold:
        return set()

    tool_names_seen: list[str] = []
    for record in non_noop:
        tool_calls = record.get("tool_calls", ())
        if not isinstance(tool_calls, (list, tuple)) or not tool_calls:
            # A substantive turn with no tool calls (text-only response)
            # represents real diversification and legitimately breaks the run.
            return set()
        for tc in tool_calls:
            if isinstance(tc, dict) and tc.get("tool_name"):
                tool_names_seen.append(str(tc["tool_name"]))

    unique = set(tool_names_seen)
    if len(unique) != 1:
        return set()

    tool = next(iter(unique))

    # Path-sensitive tools: only suppress when the same destination path is
    # repeated.  Different paths mean the agent is exploring distinct files.
    if tool in _PATH_SENSITIVE_TOOLS:
        paths: list[Optional[str]] = []
        for record in non_noop:
            tool_calls = record.get("tool_calls", ())
            if not isinstance(tool_calls, (list, tuple)):
                continue
            for tc in tool_calls:
                if isinstance(tc, dict) and str(tc.get("tool_name", "")) == tool:
                    paths.append(_extract_tool_path(tc))
        # Paths vary → genuine multi-file exploration, no suppression.
        # Any unknown path (None) → cannot confirm diversity, fall back to suppress.
        if None not in paths and len(set(paths)) > 1:
            return set()

    return unique
