"""Pure stress scalar computation — Mode A (cgroup only) and Mode B (cgroup + PSI)."""

from __future__ import annotations

from lambertian.configuration.universe_config import PainStressConfig
from lambertian.pain_monitor.cgroup_reader import ResourceSample


def compute_raw(sample: ResourceSample, stress_cfg: PainStressConfig) -> float:
    """Compute the raw composite stress value from a ResourceSample.

    Mode B (PSI blend) is used when cpu_psi_some is not None.
    Mode A (cgroup only) is used otherwise.
    """
    if sample.cpu_psi_some is not None:
        # Mode B: blend cgroup and PSI signals per cgroup_blend_weight, then apply weights.
        blend = stress_cfg.cgroup_blend_weight
        cpu_blended = blend * sample.cpu_usage_fraction + (1.0 - blend) * sample.cpu_psi_some
        if sample.memory_psi_some is not None:
            mem_blended = (
                blend * sample.memory_usage_fraction
                + (1.0 - blend) * sample.memory_psi_some
            )
        else:
            mem_blended = sample.memory_usage_fraction
        return (
            stress_cfg.cpu_weight * cpu_blended
            + stress_cfg.memory_weight * mem_blended
        )

    # Mode A: weighted sum of cgroup fractions only.
    return (
        stress_cfg.cpu_weight * sample.cpu_usage_fraction
        + stress_cfg.memory_weight * sample.memory_usage_fraction
    )


def update_ema(prior: float, raw: float, alpha: float) -> float:
    """Exponential moving average: scalar = (1 - alpha) * prior + alpha * raw."""
    return (1.0 - alpha) * prior + alpha * raw
