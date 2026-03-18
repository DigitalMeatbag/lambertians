"""IS-13.3 Pain history reader — sums severity from a byte offset."""
from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)


class PainHistoryReader:
    """IS-13.3. Reads pain_history.jsonl from byte offset, sums 'severity' field."""

    def __init__(self, pain_history_path: Path) -> None:
        self._pain_history_path = pain_history_path

    def sum_new_pain(self, from_byte_offset: int) -> tuple[float, int]:
        """Return (pain_sum, new_byte_offset). If file absent: returns (0.0, 0).

        Seeks to from_byte_offset. Skips unparseable lines.
        """
        try:
            with open(self._pain_history_path, "rb") as f:
                f.seek(from_byte_offset)
                total = 0.0
                for raw_line in f:
                    try:
                        record: object = json.loads(raw_line)
                        if not isinstance(record, dict):
                            continue
                        severity = record.get("severity")
                        if isinstance(severity, (int, float)):
                            total += float(severity)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        _log.warning(
                            "PainHistoryReader: skipping unparseable line at offset %d",
                            from_byte_offset,
                        )
                return total, f.tell()
        except FileNotFoundError:
            return 0.0, 0
