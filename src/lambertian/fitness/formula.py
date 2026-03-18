"""IS-13.3 Phase 1 baseline fitness formula."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessInputs:
    lifespan: int
    max_age: int
    meaningful_event_count: int
    expected_events_per_100_turns: float
    cumulative_pain: float
    normalized_pain_baseline: float
    minimum_denominator: float


def compute_phase1_baseline(inputs: FitnessInputs) -> float:
    """IS-13.3 formula: (lifespan/max_age) × (engagement/expected) / max(normalized_pain, min_denom)

    Edge cases:
    - lifespan == 0: return 0.0
    - expected_engagement == 0.0: treat engagement term as 1.0
    """
    if inputs.lifespan == 0:
        return 0.0
    lifespan_term = inputs.lifespan / inputs.max_age
    expected_engagement = (inputs.lifespan / 100.0) * inputs.expected_events_per_100_turns
    engagement_term = (
        1.0
        if expected_engagement == 0.0
        else inputs.meaningful_event_count / expected_engagement
    )
    normalized_pain = inputs.cumulative_pain / inputs.normalized_pain_baseline
    denominator = max(normalized_pain, inputs.minimum_denominator)
    return (lifespan_term * engagement_term) / denominator
