"""Pure functions for formatting pain messages and rendering [SYSTEM_PAIN] blocks (IS-8.5)."""

from __future__ import annotations

from lambertian.configuration.universe_config import Config
from lambertian.contracts.pain_records import PainEvent, PainMessage


def _urgency(severity: float, config: Config) -> str:
    """Derive urgency label from severity using pain.events thresholds for both channels."""
    thresholds = config.pain.events
    if severity >= thresholds.critical_threshold:
        return "critical"
    if severity >= thresholds.interrupt_threshold:
        return "interrupt"
    return "notice"


def format_stress_message(scalar: float, config: Config) -> PainMessage:
    """Produce a stress-channel PainMessage from the current EMA scalar."""
    urgency = _urgency(scalar, config)
    description = (
        f"Sustained resource pressure detected. "
        f"Stress scalar: {scalar:.4f} "
        f"(interrupt={config.pain.stress.interrupt_threshold:.2f}, "
        f"death={config.pain.stress.death_threshold:.2f})."
    )
    return PainMessage(
        channel="stress",
        severity=scalar,
        urgency=urgency,
        description=description,
        context=None,
    )


def format_event_message(event: PainEvent, config: Config) -> PainMessage:
    """Produce an event-channel PainMessage from a PainEvent."""
    urgency = _urgency(event.severity, config)
    context_line: str | None = None
    if event.context:
        context_line = "; ".join(f"{k}={v}" for k, v in event.context.items())
    return PainMessage(
        channel="event",
        severity=event.severity,
        urgency=urgency,
        description=event.description,
        context=context_line,
    )


def render_pain_block(message: PainMessage) -> str:
    """Render a PainMessage as a [SYSTEM_PAIN] text block for prompt injection."""
    lines = [
        "[SYSTEM_PAIN]",
        f"channel: {message.channel}",
        f"severity: {message.severity:.4f}",
        f"urgency: {message.urgency}",
        f"description: {message.description}",
    ]
    if message.context is not None:
        lines.append(f"context: {message.context}")
    return "\n".join(lines)
