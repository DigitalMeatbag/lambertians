"""Unit tests for pure stress scalar functions — no filesystem."""

from __future__ import annotations

import pytest

from lambertian.configuration.universe_config import PainStressConfig
from lambertian.pain_monitor.cgroup_reader import ResourceSample
from lambertian.pain_monitor.stress_scalar import compute_raw, update_ema


@pytest.fixture()
def stress_cfg() -> PainStressConfig:
    return PainStressConfig(
        scale_min=0.0,
        scale_max=1.0,
        sample_interval_seconds=5,
        ema_alpha=0.20,
        interrupt_threshold=0.70,
        death_threshold=0.90,
        death_consecutive_turns=5,
        recovery_threshold=0.60,
        cpu_weight=0.60,
        memory_weight=0.40,
        cgroup_blend_weight=0.50,
    )


def test_compute_raw_mode_a(stress_cfg: PainStressConfig) -> None:
    sample = ResourceSample(
        cpu_usage_fraction=0.80,
        memory_usage_fraction=0.50,
        cpu_psi_some=None,
        memory_psi_some=None,
    )
    result = compute_raw(sample, stress_cfg)
    expected = 0.60 * 0.80 + 0.40 * 0.50  # 0.48 + 0.20 = 0.68
    assert result == pytest.approx(expected)


def test_compute_raw_mode_a_zero(stress_cfg: PainStressConfig) -> None:
    sample = ResourceSample(
        cpu_usage_fraction=0.0,
        memory_usage_fraction=0.0,
        cpu_psi_some=None,
        memory_psi_some=None,
    )
    assert compute_raw(sample, stress_cfg) == pytest.approx(0.0)


def test_compute_raw_mode_b_cpu_psi(stress_cfg: PainStressConfig) -> None:
    sample = ResourceSample(
        cpu_usage_fraction=0.80,
        memory_usage_fraction=0.50,
        cpu_psi_some=0.60,
        memory_psi_some=None,
    )
    blend = 0.50
    cpu_blended = blend * 0.80 + (1.0 - blend) * 0.60  # 0.40 + 0.30 = 0.70
    mem_blended = 0.50  # no memory PSI — falls back to cgroup fraction
    expected = 0.60 * cpu_blended + 0.40 * mem_blended
    assert compute_raw(sample, stress_cfg) == pytest.approx(expected)


def test_compute_raw_mode_b_both_psi(stress_cfg: PainStressConfig) -> None:
    sample = ResourceSample(
        cpu_usage_fraction=0.80,
        memory_usage_fraction=0.50,
        cpu_psi_some=0.60,
        memory_psi_some=0.30,
    )
    blend = 0.50
    cpu_blended = blend * 0.80 + (1.0 - blend) * 0.60  # 0.70
    mem_blended = blend * 0.50 + (1.0 - blend) * 0.30  # 0.40
    expected = 0.60 * cpu_blended + 0.40 * mem_blended
    assert compute_raw(sample, stress_cfg) == pytest.approx(expected)


def test_update_ema_first_sample() -> None:
    # prior = 0 (first sample)
    result = update_ema(0.0, 0.80, 0.20)
    expected = (1 - 0.20) * 0.0 + 0.20 * 0.80  # 0.16
    assert result == pytest.approx(expected)


def test_update_ema_converges() -> None:
    scalar = 0.0
    for _ in range(100):
        scalar = update_ema(scalar, 1.0, 0.20)
    # After many iterations with raw=1.0, scalar should be very close to 1.0
    assert scalar == pytest.approx(1.0, abs=1e-6)


def test_update_ema_alpha_one() -> None:
    # alpha=1 means scalar = raw immediately
    result = update_ema(0.5, 0.9, 1.0)
    assert result == pytest.approx(0.9)


def test_update_ema_alpha_zero() -> None:
    # alpha=0 means scalar never changes
    result = update_ema(0.5, 0.9, 0.0)
    assert result == pytest.approx(0.5)

