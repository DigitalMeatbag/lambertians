"""Unit tests for DeliveryQueue — append messages, drain, verify atomic clear."""

from __future__ import annotations

from pathlib import Path

import pytest

from lambertian.contracts.pain_records import PainMessage
from lambertian.pain_monitor.delivery_queue import DeliveryQueue


def _make_message(channel: str = "stress", severity: float = 0.75) -> PainMessage:
    return PainMessage(
        channel=channel,
        severity=severity,
        urgency="interrupt",
        description="Test pain message.",
        context=None,
    )


def _make_event_message() -> PainMessage:
    return PainMessage(
        channel="event",
        severity=0.80,
        urgency="interrupt",
        description="Tool failed.",
        context="tool=bash; code=1",
    )


def test_drain_empty_queue(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    assert dq.drain() == []


def test_append_one_message(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    msg = _make_message()
    dq.append_message(msg)
    drained = dq.drain()
    assert len(drained) == 1
    assert drained[0].channel == "stress"
    assert drained[0].severity == pytest.approx(0.75)


def test_drain_clears_queue(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    dq.append_message(_make_message())
    dq.drain()
    # Second drain should be empty.
    assert dq.drain() == []


def test_append_multiple_messages(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    dq.append_message(_make_message("stress", 0.75))
    dq.append_message(_make_message("event", 0.85))
    drained = dq.drain()
    assert len(drained) == 2
    channels = {m.channel for m in drained}
    assert "stress" in channels
    assert "event" in channels


def test_event_message_context_preserved(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    msg = _make_event_message()
    dq.append_message(msg)
    drained = dq.drain()
    assert drained[0].context == "tool=bash; code=1"


def test_drain_returns_pain_message_instances(tmp_path: Path) -> None:
    dq = DeliveryQueue(tmp_path / "delivery_queue.json")
    dq.append_message(_make_message())
    drained = dq.drain()
    assert all(isinstance(m, PainMessage) for m in drained)


def test_append_accumulates_across_instances(tmp_path: Path) -> None:
    """Simulate pain_monitor appending, then turn_engine draining."""
    path = tmp_path / "delivery_queue.json"
    writer = DeliveryQueue(path)
    reader = DeliveryQueue(path)

    writer.append_message(_make_message("stress", 0.70))
    writer.append_message(_make_message("event", 0.90))

    drained = reader.drain()
    assert len(drained) == 2
    assert reader.drain() == []
