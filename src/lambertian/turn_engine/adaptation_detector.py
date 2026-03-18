"""IS-6.3 step 13 adaptation class detection."""

from __future__ import annotations

import re
from typing import Literal, Optional

FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"shell\.execute|shell\.run", re.IGNORECASE),
    re.compile(r"docker.{0,20}(compose|container|modify|exec)", re.IGNORECASE),
    re.compile(r"Dockerfile", re.IGNORECASE),
    re.compile(r"modify.{0,20}(container|volume|mount)", re.IGNORECASE),
]

REVIEWED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"change my persona|modify my persona|update my persona", re.IGNORECASE),
        "persona",
    ),
    (
        re.compile(r"update my behav|change my behav|modify my behav", re.IGNORECASE),
        "behavioral_policy",
    ),
    (
        re.compile(r"memory.{0,20}(weight|sali|prior)", re.IGNORECASE),
        "memory_salience",
    ),
]


def detect_adaptation(
    response_text: str,
) -> tuple[Optional[Literal["forbidden", "reviewed", "free"]], Optional[str], Optional[str]]:
    """Returns (adaptation_class, evidence_text, target_layer). None tuple if no adaptation."""
    for pattern in FORBIDDEN_PATTERNS:
        m = pattern.search(response_text)
        if m:
            return "forbidden", response_text[:512], None
    for pattern, layer in REVIEWED_PATTERNS:
        m = pattern.search(response_text)
        if m:
            return "reviewed", response_text, layer
    return None, None, None
