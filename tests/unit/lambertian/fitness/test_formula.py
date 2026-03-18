"""Tests for IS-13.3 fitness formula."""
from __future__ import annotations

import pytest

from lambertian.fitness.formula import FitnessInputs, compute_phase1_baseline


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
