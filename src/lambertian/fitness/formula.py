"""IS-13.3 fitness formulas — Phase 1 baseline and Phase 2 quality-weighted."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FitnessInputs:
    lifespan: int
    max_age: int
    meaningful_event_count: int
    expected_events_per_100_turns: float
    cumulative_pain: float
    normalized_pain_baseline: float
    minimum_denominator: float
    # Populated by scorer for quality-weighted function; ignored by phase1_baseline.
    event_type_histogram: dict[str, int] = field(default_factory=dict)


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


def compute_phase2_quality_weighted(
    inputs: FitnessInputs,
    primary_weight: float,
    repetition_weight: float,
    expected_quality_score: float,
) -> float:
    """IS-13 Phase 2 formula: quality-weighted engagement replaces raw event count.

    quality_score = Σ (over all event types)
        min(count, 1) * primary_weight + max(count - 1, 0) * repetition_weight

    The first occurrence of each unique event type earns full primary_weight credit.
    All subsequent occurrences earn fractional repetition_weight credit.
    This creates selection pressure against the boredom attractor (pure reflection loops)
    by rewarding breadth of event type diversity over mechanical repetition.

    Edge cases:
    - lifespan == 0: return 0.0
    - expected_quality_score == 0.0: treat quality term as 1.0
    """
    if inputs.lifespan == 0:
        return 0.0
    lifespan_term = inputs.lifespan / inputs.max_age

    quality_score = sum(
        min(count, 1) * primary_weight + max(count - 1, 0) * repetition_weight
        for count in inputs.event_type_histogram.values()
    )
    quality_term = (
        1.0 if expected_quality_score == 0.0 else quality_score / expected_quality_score
    )
    normalized_pain = inputs.cumulative_pain / inputs.normalized_pain_baseline
    denominator = max(normalized_pain, inputs.minimum_denominator)
    return (lifespan_term * quality_term) / denominator
