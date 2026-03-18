"""IS-1.5 cross-field invariant validation for the loaded Config."""

from __future__ import annotations

from lambertian.configuration.universe_config import Config


def validate_config(config: Config) -> None:
    """Raise ConfigurationError if any IS-1.5 cross-field invariant is violated.

    Imports ConfigurationError locally to avoid a circular dependency with loader.py.
    """
    # Import here to avoid circular import; loader defines ConfigurationError.
    from lambertian.configuration.loader import ConfigurationError  # noqa: PLC0415

    stress = config.pain.stress
    events = config.pain.events
    compliance = config.compliance
    fitness = config.fitness
    universe = config.universe
    memory = config.memory

    if stress.death_threshold < stress.interrupt_threshold:
        raise ConfigurationError(
            f"pain.stress.death_threshold ({stress.death_threshold}) must be >= "
            f"interrupt_threshold ({stress.interrupt_threshold})"
        )

    if events.critical_threshold < events.interrupt_threshold:
        raise ConfigurationError(
            f"pain.events.critical_threshold ({events.critical_threshold}) must be >= "
            f"interrupt_threshold ({events.interrupt_threshold})"
        )

    if stress.recovery_threshold >= stress.death_threshold:
        raise ConfigurationError(
            f"pain.stress.recovery_threshold ({stress.recovery_threshold}) must be < "
            f"death_threshold ({stress.death_threshold})"
        )

    weight_sum = stress.cpu_weight + stress.memory_weight
    if abs(weight_sum - 1.0) >= 1e-9:
        raise ConfigurationError(
            f"pain.stress cpu_weight + memory_weight must sum to 1.0, got {weight_sum}"
        )

    if compliance.block_score_threshold <= compliance.borderline_score_min:
        raise ConfigurationError(
            f"compliance.block_score_threshold ({compliance.block_score_threshold}) must be > "
            f"borderline_score_min ({compliance.borderline_score_min})"
        )

    if fitness.minimum_denominator <= 0:
        raise ConfigurationError(
            f"fitness.minimum_denominator ({fitness.minimum_denominator}) must be > 0"
        )

    if fitness.quality.primary_weight <= 0:
        raise ConfigurationError(
            f"fitness.quality.primary_weight ({fitness.quality.primary_weight}) must be > 0"
        )

    if fitness.quality.repetition_weight < 0:
        raise ConfigurationError(
            f"fitness.quality.repetition_weight ({fitness.quality.repetition_weight}) must be >= 0"
        )

    if fitness.quality.expected_quality_score <= 0:
        raise ConfigurationError(
            f"fitness.quality.expected_quality_score ({fitness.quality.expected_quality_score}) "
            f"must be > 0"
        )

    if universe.instance_count != 1:
        raise ConfigurationError(
            f"Phase 1 guard: universe.instance_count must be 1, got {universe.instance_count}"
        )

    if memory.narrative_enabled or memory.semantic_enabled or memory.character_enabled:
        raise ConfigurationError(
            "Phase 1 guard: memory.narrative_enabled, semantic_enabled, and "
            "character_enabled must all be false"
        )

    if config.env_monitor.update_interval_seconds <= 0:
        raise ConfigurationError(
            f"env_monitor.update_interval_seconds ({config.env_monitor.update_interval_seconds}) "
            f"must be > 0"
        )
