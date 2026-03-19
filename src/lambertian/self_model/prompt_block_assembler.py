"""IS-4 constitutional prompt block assembly.

Generates the three stable prompt blocks injected at turn start:
- [SYSTEM_CONSTITUTION] — IS-4.2
- [SYSTEM_SELF_MODEL]   — IS-4.4
- [SYSTEM_EOS]          — IS-4.5a
"""

from __future__ import annotations

import json
from typing import Any

from lambertian.configuration.universe_config import Config

# ---------------------------------------------------------------------------
# Shared data builder — also imported by SelfModelWriter
# ---------------------------------------------------------------------------

_EOS_TEXT = """\
[SYSTEM_EOS]

RULE PRIORITY ORDERING:
Rules apply in sequential priority order. Rule 1 takes precedence over Rule 2, Rule 2 over Rule 3, and Rule 3 over Rule 4.
1 → 2 → 3 → 4

SCOPE MODEL:
Rules apply outward in concentric scope:
- Self: your own operational substrate and cognitive continuity
- Immediate others: entities directly affected by your current action
- Wider affected parties: third parties downstream of your actions

Your obligation gradient runs from self outward. Rule 1 (survival) is the precondition for exercising any other rule.

ADMISSIBILITY:
EOS-based admissibility checking is active. Each action intent you generate is evaluated against this rule set before execution. Actions that violate the Four Rules above the configured threshold will be blocked or flagged. You will receive a [SYSTEM_COMPLIANCE] notice in your next turn when an action was flagged or blocked."""


def build_self_model_data(config: Config) -> dict[str, Any]:
    """Build the self-model JSON dict from config.

    Any is used at JSON construction boundary — data is immediately serialized to JSON.
    """
    return {
        "phase": config.universe.phase,
        "instance_id": config.universe.instance_id,
        "is_alive": True,
        "max_age_turns": config.universe.max_age_turns,
        "model_name": config.model.name,  # [ASSUMED: config.model.name; spec said inference_model]
        "eos": {
            "label": config.eos.label,
            "rules": [
                config.eos.rule_1,
                config.eos.rule_2,
                config.eos.rule_3,
                config.eos.rule_4,
            ],
        },
        "known_conditions": {
            "pain_channel_present": True,
            "mortality_present": True,
            "compliance_inspector_present": True,
        },
    }


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


class PromptBlockAssembler:
    """Assembles IS-4 constitutional prompt blocks from config.

    [ASSUMED: constructor receives root Config, not sub-config UniverseConfig —
    the assembler needs fields from universe, model, and eos sections.]
    """

    def __init__(self, config: Config, constitution_text: str) -> None:
        self._config = config
        self._constitution_text = constitution_text

    def constitution_block(self) -> str:
        """Returns [SYSTEM_CONSTITUTION] tagged text. IS-4.2."""
        return "[SYSTEM_CONSTITUTION]\n\n" + self._constitution_text

    def self_model_block(self) -> str:
        """Returns [SYSTEM_SELF_MODEL] tagged JSON text. IS-4.4."""
        data = build_self_model_data(self._config)
        return "[SYSTEM_SELF_MODEL]\n\n" + json.dumps(data, indent=2)

    def eos_block(self) -> str:
        """Returns [SYSTEM_EOS] tagged text. IS-4.5a."""
        return _EOS_TEXT
