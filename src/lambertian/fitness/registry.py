"""IS-13 pluggable fitness function registry."""
from __future__ import annotations

from typing import Protocol

from lambertian.fitness.formula import FitnessInputs, compute_phase1_baseline


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


def build_default_registry() -> FitnessFunctionRegistry:
    """Build and return the default registry with 'phase1_baseline' registered."""
    registry = FitnessFunctionRegistry()

    class _Phase1Baseline:
        def compute(self, inputs: FitnessInputs) -> float:
            return compute_phase1_baseline(inputs)

    registry.register("phase1_baseline", _Phase1Baseline())
    return registry
