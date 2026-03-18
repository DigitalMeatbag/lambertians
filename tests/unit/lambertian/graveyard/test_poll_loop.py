"""Tests for GraveyardPollLoop."""
from __future__ import annotations

from unittest.mock import MagicMock, call

from lambertian.contracts.pain_records import DeathRecord
from lambertian.graveyard.poll_loop import GraveyardPollLoop


def _make_death_record() -> DeathRecord:
    return DeathRecord(
        instance_id="test-001",
        trigger="max_age",
        trigger_value=1000.0,
        threshold_used=1000.0,
        turn_number=1000,
        timestamp="2024-01-01T00:00:00+00:00",
    )


def test_polls_multiple_times_before_death(monkeypatch: object) -> None:
    """Verify the loop keeps polling when no death record is present, then stops."""
    import lambertian.graveyard.poll_loop as poll_module

    sleep_calls: list[float] = []
    monkeypatch.setattr(poll_module.time, "sleep", lambda s: sleep_calls.append(s))  # type: ignore[attr-defined]

    death = _make_death_record()
    death_reader = MagicMock()
    death_reader.read.side_effect = [None, None, death]

    harvest_sequence = MagicMock()
    loop = GraveyardPollLoop(death_reader, harvest_sequence)
    loop.run()

    # Should have slept twice (once after each None)
    assert len(sleep_calls) == 2
    assert all(s == 2 for s in sleep_calls)


def test_harvest_called_exactly_once_on_death(monkeypatch: object) -> None:
    import lambertian.graveyard.poll_loop as poll_module

    monkeypatch.setattr(poll_module.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

    death = _make_death_record()
    death_reader = MagicMock()
    death_reader.read.side_effect = [None, death]

    harvest_sequence = MagicMock()
    loop = GraveyardPollLoop(death_reader, harvest_sequence)
    loop.run()

    harvest_sequence.execute.assert_called_once()


def test_run_returns_after_harvest(monkeypatch: object) -> None:
    import lambertian.graveyard.poll_loop as poll_module

    monkeypatch.setattr(poll_module.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

    death = _make_death_record()
    death_reader = MagicMock()
    death_reader.read.return_value = death

    harvest_sequence = MagicMock()
    loop = GraveyardPollLoop(death_reader, harvest_sequence)
    loop.run()  # should return, not block

    harvest_sequence.execute.assert_called_once()
    # Only one read call — returned immediately
    assert death_reader.read.call_count == 1
