"""IS-13 pluggable fitness function registry."""
from __future__ import annotations

from typing import Optional, Protocol

from lambertian.configuration.universe_config import FitnessQualityConfig
from lambertian.fitness.formula import (
    FitnessInputs,
    compute_phase1_baseline,
    compute_phase2_quality_weighted,
)


class FitnessFunction(Protocol):
    def compute(self, inputs: FitnessInputs) -> float: ...


class FitnessFunctionRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, FitnessFunction] = {}

    def register(self, key: str, fn: FitnessFunction) -> None:
        self._registry[key] = fn

    def get(self, key: str) -> FitnessFunction:
        """Return the registered function for key. Raises KeyError if not registered."""
        return self._registry[key]


def build_default_registry(
    quality_config: Optional[FitnessQualityConfig] = None,
) -> FitnessFunctionRegistry:
    """Build and return the default registry with all standard functions registered.

    phase1_baseline: always registered with fixed formula.
    phase2_quality_weighted: registered if quality_config is provided; uses its weight knobs.
    """
    registry = FitnessFunctionRegistry()

    class _Phase1Baseline:
        def compute(self, inputs: FitnessInputs) -> float:
            return compute_phase1_baseline(inputs)

    registry.register("phase1_baseline", _Phase1Baseline())

    if quality_config is not None:
        _pw = quality_config.primary_weight
        _rw = quality_config.repetition_weight
        _eq = quality_config.expected_quality_score

        class _Phase2QualityWeighted:
            def compute(self, inputs: FitnessInputs) -> float:
                return compute_phase2_quality_weighted(inputs, _pw, _rw, _eq)

        registry.register("phase2_quality_weighted", _Phase2QualityWeighted())

    return registry
