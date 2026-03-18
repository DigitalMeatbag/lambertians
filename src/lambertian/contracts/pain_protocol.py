"""Protocols for pain channel interaction between turn_engine and pain_monitor (IS-8.6, IS-8.7)."""

from __future__ import annotations

from typing import Protocol

from lambertian.contracts.pain_records import PainEvent, PainMessage


class PainEventSubmitter(Protocol):
    """Submits a pain event to the event queue (IS-8.7)."""

    def submit(self, event: PainEvent) -> None: ...


class PainDeliveryDrain(Protocol):
    """Drains the delivery queue for one turn (IS-8.6)."""

    def drain(self) -> list[PainMessage]: ...
