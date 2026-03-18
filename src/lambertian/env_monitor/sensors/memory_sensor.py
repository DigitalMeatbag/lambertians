"""Memory sensor — available/used/total via psutil."""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


class MemorySensor:
    """Returns memory dict: total_gb, available_gb, used_percent."""

    def collect(self) -> dict[str, Any]:
        try:
            import psutil  # type: ignore[import-untyped]
        except ImportError:
            _log.warning("psutil not available — memory sensor returning empty")
            return {}

        try:
            vm = psutil.virtual_memory()
            return {
                "memory": {
                    "total_gb": round(vm.total / (1024 ** 3), 2),
                    "available_gb": round(vm.available / (1024 ** 3), 2),
                    "used_percent": vm.percent,
                }
            }
        except Exception as exc:
            _log.warning("MemorySensor.collect failed: %s", exc)
            return {}
