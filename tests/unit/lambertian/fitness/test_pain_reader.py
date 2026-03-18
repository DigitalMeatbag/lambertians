"""Tests for PainHistoryReader."""
from __future__ import annotations

import json
from pathlib import Path

from lambertian.fitness.pain_reader import PainHistoryReader


def _write_pain_events(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_sum_pain_from_offset_zero(tmp_path: Path) -> None:
    pain_file = tmp_path / "pain_history.jsonl"
    _write_pain_events(
        pain_file,
        [
            {"severity": 0.5, "incident_type": "tool_failure"},
            {"severity": 0.3, "incident_type": "retrieval_miss"},
            {"severity": 0.2, "incident_type": "mcp_rejection"},
        ],
    )
    reader = PainHistoryReader(pain_file)
    total, offset = reader.sum_new_pain(0)
    assert abs(total - 1.0) < 1e-9
    assert offset == pain_file.stat().st_size


def test_cursor_advances(tmp_path: Path) -> None:
    pain_file = tmp_path / "pain_history.jsonl"
    _write_pain_events(pain_file, [{"severity": 0.4}])
    reader = PainHistoryReader(pain_file)
    _, offset = reader.sum_new_pain(0)
    assert offset == pain_file.stat().st_size


def test_absent_file_returns_zero(tmp_path: Path) -> None:
    reader = PainHistoryReader(tmp_path / "nonexistent.jsonl")
    total, offset = reader.sum_new_pain(0)
    assert total == 0.0
    assert offset == 0


def test_skips_unparseable_lines(tmp_path: Path) -> None:
    pain_file = tmp_path / "pain_history.jsonl"
    pain_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pain_file, "w", encoding="utf-8") as f:
        f.write('{"severity": 0.5}\n')
        f.write("not valid json\n")
        f.write('{"severity": 0.3}\n')

    reader = PainHistoryReader(pain_file)
    total, _ = reader.sum_new_pain(0)
    assert abs(total - 0.8) < 1e-9


def test_sum_from_mid_file_offset(tmp_path: Path) -> None:
    pain_file = tmp_path / "pain_history.jsonl"
    records = [{"severity": 0.5}, {"severity": 0.3}]
    _write_pain_events(pain_file, records)

    first_line_bytes = len((json.dumps(records[0]) + "\n").encode("utf-8"))
    reader = PainHistoryReader(pain_file)
    total, _ = reader.sum_new_pain(first_line_bytes)
    assert abs(total - 0.3) < 1e-9
