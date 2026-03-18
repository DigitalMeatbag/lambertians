"""Tests for IS-13.3 fitness formula — Phase 1 baseline and Phase 2 quality-weighted."""
from __future__ import annotations

import pytest

from lambertian.fitness.formula import (
    FitnessInputs,
    compute_phase1_baseline,
    compute_phase2_quality_weighted,
)


def _make_inputs(**kwargs: object) -> FitnessInputs:
    defaults = dict(
        lifespan=100,
        max_age=1000,
        meaningful_event_count=25,
        expected_events_per_100_turns=25.0,
        cumulative_pain=5.0,
        normalized_pain_baseline=10.0,
        minimum_denominator=0.10,
    )
    defaults.update(kwargs)  # type: ignore[arg-type]
    return FitnessInputs(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Phase 1 baseline
# ---------------------------------------------------------------------------

def test_lifespan_zero_returns_zero() -> None:
    inputs = _make_inputs(lifespan=0)
    assert compute_phase1_baseline(inputs) == 0.0


def test_zero_expected_events_engagement_term_is_one() -> None:
    # expected_events_per_100_turns = 0 → expected_engagement = 0 → engagement_term = 1.0
    inputs = _make_inputs(expected_events_per_100_turns=0.0, meaningful_event_count=99)
    result = compute_phase1_baseline(inputs)
    # lifespan=100, max_age=1000 → lifespan_term = 0.1
    # engagement_term = 1.0
    # cumulative_pain=5, baseline=10 → normalized_pain=0.5 > min_denom=0.10
    # score = 0.1 * 1.0 / 0.5 = 0.2
    assert result == pytest.approx(0.2)


def test_normal_case() -> None:
    # lifespan=100, max_age=1000, events=25, expected_per_100=25, pain=5, baseline=10, min=0.10
    # lifespan_term = 0.1
    # expected_engagement = (100/100)*25 = 25
    # engagement_term = 25/25 = 1.0
    # normalized_pain = 5/10 = 0.5 > 0.10
    # score = 0.1 * 1.0 / 0.5 = 0.2
    inputs = _make_inputs()
    assert compute_phase1_baseline(inputs) == pytest.approx(0.2)


def test_high_pain_uses_normalized_pain_not_min_denom() -> None:
    # cumulative_pain=100, baseline=10 → normalized_pain=10 >> min_denom=0.10
    inputs = _make_inputs(cumulative_pain=100.0)
    # lifespan_term=0.1, engagement_term=1.0, denominator=10
    # score = 0.1 / 10 = 0.01
    assert compute_phase1_baseline(inputs) == pytest.approx(0.01)


def test_min_denominator_floor_applies() -> None:
    # cumulative_pain very small → normalized_pain < min_denom → uses min_denom
    inputs = _make_inputs(cumulative_pain=0.001, minimum_denominator=0.10)
    # lifespan_term=0.1, engagement=1.0, normalized_pain=0.0001, denominator=0.10
    # score = 0.1 / 0.10 = 1.0
    assert compute_phase1_baseline(inputs) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Phase 2 quality-weighted
# ---------------------------------------------------------------------------

def _make_quality_inputs(**kwargs: object) -> FitnessInputs:
    defaults = dict(
        lifespan=100,
        max_age=1000,
        meaningful_event_count=0,  # unused by quality formula
        expected_events_per_100_turns=0.0,  # unused by quality formula
        cumulative_pain=5.0,
        normalized_pain_baseline=10.0,
        minimum_denominator=0.10,
        event_type_histogram={},
    )
    defaults.update(kwargs)  # type: ignore[arg-type]
    return FitnessInputs(**defaults)  # type: ignore[arg-type]


_PW = 1.0
_RW = 0.1
_EQ = 500.0


def test_quality_lifespan_zero_returns_zero() -> None:
    inputs = _make_quality_inputs(lifespan=0)
    assert compute_phase2_quality_weighted(inputs, _PW, _RW, _EQ) == 0.0


def test_quality_empty_histogram_gives_zero_quality_term() -> None:
    # No events → quality_score = 0 → quality_term = 0 / 500 = 0.0
    inputs = _make_quality_inputs(event_type_histogram={})
    # lifespan_term = 100/1000 = 0.1, quality_term = 0.0, denominator = max(0.5, 0.1) = 0.5
    # score = 0.1 * 0.0 / 0.5 = 0.0
    result = compute_phase2_quality_weighted(inputs, _PW, _RW, _EQ)
    assert result == pytest.approx(0.0)


def test_quality_zero_expected_quality_score_treats_term_as_one() -> None:
    inputs = _make_quality_inputs(event_type_histogram={"TOOL_CALL": 5})
    # expected_quality_score=0 → quality_term = 1.0
    # lifespan=0.1, quality_term=1.0, pain=0.5 > 0.1
    # score = 0.1 / 0.5 = 0.2
    result = compute_phase2_quality_weighted(inputs, _PW, _RW, 0.0)
    assert result == pytest.approx(0.2)


def test_quality_single_event_type_once_gets_primary_weight() -> None:
    # TOOL_CALL: count=1 → quality_score = min(1,1)*1.0 + max(0,0)*0.1 = 1.0
    # quality_term = 1.0 / 500.0 = 0.002
    # lifespan_term = 100/1000 = 0.1
    # normalized_pain = 5/10 = 0.5, denominator = 0.5
    # score = 0.1 * 0.002 / 0.5 = 0.0004
    inputs = _make_quality_inputs(event_type_histogram={"TOOL_CALL": 1})
    result = compute_phase2_quality_weighted(inputs, _PW, _RW, _EQ)
    assert result == pytest.approx(0.0004)


def test_quality_single_event_type_repeated_adds_repetition_weight() -> None:
    # TOOL_CALL: count=10 → quality_score = 1*1.0 + 9*0.1 = 1.9
    # quality_term = 1.9 / 500.0 = 0.0038
    # score = 0.1 * 0.0038 / 0.5 = 0.00076
    inputs = _make_quality_inputs(event_type_histogram={"TOOL_CALL": 10})
    result = compute_phase2_quality_weighted(inputs, _PW, _RW, _EQ)
    assert result == pytest.approx(0.00076)


def test_quality_diverse_event_types_score_higher_than_repetition() -> None:
    # 10 unique event types × 1 occurrence each vs 1 type × 10 occurrences
    diverse = _make_quality_inputs(
        event_type_histogram={f"TYPE_{i}": 1 for i in range(10)}
    )
    repetitive = _make_quality_inputs(event_type_histogram={"TOOL_CALL": 10})

    diverse_score = compute_phase2_quality_weighted(diverse, _PW, _RW, _EQ)
    repetitive_score = compute_phase2_quality_weighted(repetitive, _PW, _RW, _EQ)

    # diverse: quality_score = 10 * 1.0 = 10.0
    # repetitive: quality_score = 1.0 + 9*0.1 = 1.9
    assert diverse_score > repetitive_score


def test_quality_formula_rewards_breadth_vs_boredom_attractor() -> None:
    # Realistic boredom attractor: 100 turns of pure reflection.
    # TURN_COMPLETE is not in MEANINGFUL_EVENT_TYPES, so the event reader never tracks it.
    # Result: near-empty histogram — only one stray tool call.
    bored = _make_quality_inputs(
        lifespan=100,
        event_type_histogram={"TOOL_CALL": 1},  # one event in 100 turns
    )
    # Engaged instance: 10 different meaningful event types, 10 occurrences each
    engaged = _make_quality_inputs(
        lifespan=100,
        event_type_histogram={f"EVT_{i}": 10 for i in range(10)},
    )

    bored_score = compute_phase2_quality_weighted(bored, _PW, _RW, _EQ)
    engaged_score = compute_phase2_quality_weighted(engaged, _PW, _RW, _EQ)

    # bored: quality_score=1.0, quality_term=0.002 → score ≈ 0.0004
    # engaged: quality_score=19.0, quality_term=0.038 → score ≈ 0.0076
    # engaged is ~19x higher than bored
    assert engaged_score > bored_score * 10


def test_quality_uses_min_denominator_when_pain_low() -> None:
    # Very low pain → min denominator floor applies
    inputs = _make_quality_inputs(
        cumulative_pain=0.001,
        event_type_histogram={"TOOL_CALL": 1},
    )
    # quality_score = 1.0, quality_term = 1.0/500.0 = 0.002
    # normalized_pain = 0.001/10 = 0.0001 < min_denom=0.1 → use 0.1
    # score = 0.1 * 0.002 / 0.1 = 0.002
    result = compute_phase2_quality_weighted(inputs, _PW, _RW, _EQ)
    assert result == pytest.approx(0.002)

