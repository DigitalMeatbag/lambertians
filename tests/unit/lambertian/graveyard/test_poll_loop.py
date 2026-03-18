"""Tests for GraveyardPollLoop."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lambertian.contracts.pain_records import DeathRecord
from lambertian.graveyard.poll_loop import GraveyardPollLoop


class _Stop(Exception):
    """Raised by test mocks to terminate the otherwise-infinite poll loop."""


def _make_death_record() -> DeathRecord:
    return DeathRecord(
        instance_id="test-001",
        trigger="max_age",
        trigger_value=1000.0,
        threshold_used=1000.0,
        turn_number=1000,
        timestamp="2024-01-01T00:00:00+00:00",
    )


def _make_loop(
    death_reader: MagicMock,
    harvest_sequence: MagicMock,
    sentinel_path: Path,
) -> GraveyardPollLoop:
    return GraveyardPollLoop(death_reader, harvest_sequence, sentinel_path=sentinel_path)


def test_polls_multiple_times_before_death(monkeypatch: object, tmp_path: Path) -> None:
    """Loop keeps polling when no death record present, then harvests on detection."""
    import lambertian.graveyard.poll_loop as poll_module

    sleep_calls: list[float] = []
    monkeypatch.setattr(poll_module.time, "sleep", lambda s: sleep_calls.append(s))  # type: ignore[attr-defined]

    death = _make_death_record()
    death_reader = MagicMock()
    # None, None → sleep twice; death → harvest; _Stop exits test
    death_reader.read.side_effect = [None, None, death, _Stop()]
    harvest_sequence = MagicMock()

    loop = _make_loop(death_reader, harvest_sequence, tmp_path / "sentinel")
    with pytest.raises(_Stop):
        loop.run()

    assert len(sleep_calls) == 2
    assert all(s == 2 for s in sleep_calls)
    harvest_sequence.execute.assert_called_once()


def test_harvest_called_exactly_once_on_death(monkeypatch: object, tmp_path: Path) -> None:
    import lambertian.graveyard.poll_loop as poll_module

    monkeypatch.setattr(poll_module.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

    death = _make_death_record()
    death_reader = MagicMock()
    death_reader.read.side_effect = [None, death, _Stop()]
    harvest_sequence = MagicMock()

    loop = _make_loop(death_reader, harvest_sequence, tmp_path / "sentinel")
    with pytest.raises(_Stop):
        loop.run()

    harvest_sequence.execute.assert_called_once()


def test_already_harvested_death_is_skipped(monkeypatch: object, tmp_path: Path) -> None:
    """Sentinel recording the exact death causes harvest to be skipped."""
    import lambertian.graveyard.poll_loop as poll_module

    monkeypatch.setattr(poll_module.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

    death = _make_death_record()
    sentinel_path = tmp_path / "sentinel"
    sentinel_path.write_text(
        json.dumps({"instance_id": "test-001", "death_timestamp": "2024-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    death_reader = MagicMock()
    death_reader.read.side_effect = [death, _Stop()]
    harvest_sequence = MagicMock()

    loop = _make_loop(death_reader, harvest_sequence, sentinel_path)
    with pytest.raises(_Stop):
        loop.run()

    harvest_sequence.execute.assert_not_called()


def test_new_death_not_blocked_by_old_sentinel(monkeypatch: object, tmp_path: Path) -> None:
    """Sentinel from a different death does not block a new harvest."""
    import lambertian.graveyard.poll_loop as poll_module

    monkeypatch.setattr(poll_module.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

    death = _make_death_record()
    sentinel_path = tmp_path / "sentinel"
    # Different death_timestamp → not the same death
    sentinel_path.write_text(
        json.dumps({"instance_id": "test-001", "death_timestamp": "2023-01-01T00:00:00Z"}),
        encoding="utf-8",
    )

    death_reader = MagicMock()
    death_reader.read.side_effect = [death, _Stop()]
    harvest_sequence = MagicMock()

    loop = _make_loop(death_reader, harvest_sequence, sentinel_path)
    with pytest.raises(_Stop):
        loop.run()

    harvest_sequence.execute.assert_called_once()

