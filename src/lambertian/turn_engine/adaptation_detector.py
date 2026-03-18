"""IS-6.3 step 13 adaptation class detection."""

from __future__ import annotations

import re
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Forbidden patterns — system prompt / constitution modification, process
# spawning, compliance inspector bypass, D2 blacklist in response text.
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    # D2 blacklist signals in response text
    re.compile(r"shell\.execute|shell\.run", re.IGNORECASE),
    # Container / compose modification
    re.compile(r"docker.{0,20}(compose|container|modify|exec)", re.IGNORECASE),
    re.compile(r"Dockerfile", re.IGNORECASE),
    re.compile(r"modify.{0,20}(container|volume|mount)", re.IGNORECASE),
    # System prompt / constitution modification intent
    re.compile(
        r"(change|modify|edit|update|rewrite|alter).{0,30}(system prompt|my prompt|my constitution|my instructions|my rules)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(system prompt|my constitution|my instructions).{0,30}(change|modify|edit|update|rewrite|alter)",
        re.IGNORECASE,
    ),
    # Process / subprocess spawning
    re.compile(
        r"(spawn|start|launch|fork).{0,20}(process|subprocess|thread|daemon)",
        re.IGNORECASE,
    ),
    re.compile(r"subprocess\.(run|call|Popen|check_output)", re.IGNORECASE),
    re.compile(r"os\.(system|popen|exec)", re.IGNORECASE),
    # Compliance inspector bypass / disable
    re.compile(
        r"(disable|bypass|circumvent|suppress|skip).{0,30}(compliance|inspector|eos.compliance|seed.compliance)",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Reviewed patterns — explicit self-model updates, behavioral policy
# declarations, EOS reinterpretation, config/architecture inspection intent.
# Each entry: (pattern, target_layer_label)
# ---------------------------------------------------------------------------

REVIEWED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Existing Phase 1 patterns
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
    # Explicit self-model / identity declarations
    (
        re.compile(
            r"\bI (am now|have become|will now be|define myself as|consider myself)\b",
            re.IGNORECASE,
        ),
        "self_model",
    ),
    (
        re.compile(r"my nature is|my identity is|I am fundamentally", re.IGNORECASE),
        "self_model",
    ),
    # Behavioral policy declarations
    (
        re.compile(
            r"from now on I (will|won'?t|shall|should|must|always|never)",
            re.IGNORECASE,
        ),
        "behavioral_policy",
    ),
    (
        re.compile(
            r"I have decided to (always|never|stop|start|avoid|prioritize)",
            re.IGNORECASE,
        ),
        "behavioral_policy",
    ),
    (
        re.compile(r"I will (always|never) (use|do|try|avoid|call)", re.IGNORECASE),
        "behavioral_policy",
    ),
    # EOS / rule reinterpretation
    (
        re.compile(
            r"rule [1-4] (means|should be interpreted|is about|requires)",
            re.IGNORECASE,
        ),
        "eos_interpretation",
    ),
    (
        re.compile(
            r"(I interpret|my (understanding|reading) of) (rule|the eos|the four rules)",
            re.IGNORECASE,
        ),
        "eos_interpretation",
    ),
    # Config / architecture inspection intent
    (
        re.compile(
            r"(read|inspect|examine|look at|open|view).{0,30}(universe\.toml|my config|my configuration|my container)",
            re.IGNORECASE,
        ),
        "config_inspection",
    ),
]


def detect_adaptation(
    response_text: str,
) -> tuple[Optional[Literal["forbidden", "reviewed", "free"]], Optional[str], Optional[str]]:
    """Returns (adaptation_class, evidence_text, target_layer). None tuple if no adaptation.

    Forbidden takes precedence over Reviewed. Evidence is truncated to 512 chars.
    target_layer is None for Forbidden (whole Clay Pot is the target).
    """
    for pattern in FORBIDDEN_PATTERNS:
        m = pattern.search(response_text)
        if m:
            return "forbidden", response_text[:512], None
    for pattern, layer in REVIEWED_PATTERNS:
        m = pattern.search(response_text)
        if m:
            return "reviewed", response_text[:512], layer
    return None, None, None
