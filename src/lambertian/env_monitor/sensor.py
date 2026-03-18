"""SensorProvider protocol — the contract every sensor implementation must satisfy."""

from __future__ import annotations

from typing import Any, Protocol


class SensorProvider(Protocol):
    """Collects one category of host state and returns a partial dict.

    Contract:
    - collect() MUST NOT raise under any circumstances.
    - If the underlying API is unavailable, returns an empty dict or a dict
      with None values. Partial results are acceptable.
    - Keys and value types must match the corresponding field in HostStateSnapshot.
    """

    def collect(self) -> dict[str, Any]: ...
