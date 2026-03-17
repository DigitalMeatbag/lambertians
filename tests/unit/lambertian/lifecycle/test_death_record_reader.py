"""Unit tests for DeathRecordReader — valid record, absent file, malformed file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lambertian.lifecycle.death_record_reader import DeathRecordParseError, DeathRecordReader


def _write_valid_record(path: Path) -> None:
    record = {
        "instance_id": "lambertian-001",
        "trigger": "stress_sustained",
        "trigger_value": 0.92,
        "threshold_used": 0.90,
        "turn_number": 500,
        "timestamp": "2024-01-01T12:00:00+00:00",
    }
    path.write_text(json.dumps(record))


def test_is_dead_when_file_exists(tmp_path: Path) -> None:
    death_path = tmp_path / "death.json"
    _write_valid_record(death_path)
    reader = DeathRecordReader(death_path)
    assert reader.is_dead() is True


def test_is_dead_when_file_absent(tmp_path: Path) -> None:
    reader = DeathRecordReader(tmp_path / "death.json")
    assert reader.is_dead() is False


def test_read_returns_correct_record(tmp_path: Path) -> None:
    death_path = tmp_path / "death.json"
    _write_valid_record(death_path)
    reader = DeathRecordReader(death_path)
    record = reader.read()
    assert record is not None
    assert record.instance_id == "lambertian-001"
    assert record.trigger == "stress_sustained"
    assert record.trigger_value == pytest.approx(0.92)
    assert record.threshold_used == pytest.approx(0.90)
    assert record.turn_number == 500
    assert record.timestamp == "2024-01-01T12:00:00+00:00"


def test_read_returns_none_when_absent(tmp_path: Path) -> None:
    reader = DeathRecordReader(tmp_path / "death.json")
    assert reader.read() is None


def test_read_raises_on_malformed_json(tmp_path: Path) -> None:
    death_path = tmp_path / "death.json"
    death_path.write_text("{not valid json}")
    reader = DeathRecordReader(death_path)
    with pytest.raises(DeathRecordParseError):
        reader.read()


def test_read_raises_on_missing_field(tmp_path: Path) -> None:
    death_path = tmp_path / "death.json"
    # Missing required fields.
    death_path.write_text(json.dumps({"instance_id": "test"}))
    reader = DeathRecordReader(death_path)
    with pytest.raises(DeathRecordParseError):
        reader.read()


def test_read_raises_on_wrong_type(tmp_path: Path) -> None:
    death_path = tmp_path / "death.json"
    # trigger_value as string instead of numeric.
    record = {
        "instance_id": "test",
        "trigger": "max_age",
        "trigger_value": "not-a-float",
        "threshold_used": 1000.0,
        "turn_number": 1000,
        "timestamp": "2024-01-01T00:00:00+00:00",
    }
    death_path.write_text(json.dumps(record))
    reader = DeathRecordReader(death_path)
    with pytest.raises(DeathRecordParseError):
        reader.read()
