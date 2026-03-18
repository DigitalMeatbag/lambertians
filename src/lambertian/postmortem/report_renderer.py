"""IS-12 Phase 2 — renders post-mortem data as human-readable text."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from lambertian.postmortem.models import PostMortemData

_WIDE = 60
_SEP_HEAVY = "═" * _WIDE


def render(data: PostMortemData) -> str:
    """Render a full post-mortem report as a string."""
    sections = [
        _render_header(data),
        _render_death(data),
        _render_lifespan(data),
        _render_fitness(data),
        _render_engagement(data),
        _render_pain(data),
        _render_adaptations(data),
        _render_working_memory(data),
        _render_death_record_verbatim(data),
        _SEP_HEAVY,
    ]
    return "\n".join(s for s in sections if s)


def _section(label: str) -> str:
    """Build a section header line padded to _WIDE chars."""
    prefix = f"── {label} "
    fill = max(0, _WIDE - len(prefix))
    return f"\n{prefix}{'─' * fill}"


def _render_header(data: PostMortemData) -> str:
    instance_id = (
        data.death.instance_id
        if data.death
        else data.manifest.instance_id
        if data.manifest
        else data.artifact_dir.name
    )
    birth_ts: Optional[str] = data.events.startup_timestamp if data.events else None
    death_ts: Optional[str] = (
        data.death.timestamp
        if data.death
        else data.manifest.death_timestamp
        if data.manifest
        else None
    )
    duration_str = f"  ({_format_duration(birth_ts, death_ts)})" if birth_ts and death_ts else ""
    lines = [_SEP_HEAVY, f"  POST-MORTEM: {instance_id}"]
    if birth_ts:
        lines.append(f"  Born: {birth_ts}")
    if death_ts:
        lines.append(f"  Died: {death_ts}{duration_str}")
    lines.append(_SEP_HEAVY)
    return "\n".join(lines)


def _render_death(data: PostMortemData) -> str:
    if not data.death:
        return ""
    d = data.death
    return "\n".join([
        _section("DEATH"),
        f"  Trigger:    {d.trigger}",
        f"  Value:      {d.trigger_value:.4f}  (threshold: {d.threshold_used:.4f})",
        f"  Turn:       {d.turn_number}",
        f"  Timestamp:  {d.timestamp}",
    ])


def _render_lifespan(data: PostMortemData) -> str:
    turns: Optional[int] = (
        data.fitness.lifespan
        if data.fitness
        else data.death.turn_number
        if data.death
        else None
    )
    birth_ts: Optional[str] = data.events.startup_timestamp if data.events else None
    death_ts: Optional[str] = (
        data.death.timestamp
        if data.death
        else data.manifest.death_timestamp
        if data.manifest
        else None
    )
    duration_str = _format_duration(birth_ts, death_ts) if birth_ts and death_ts else "unknown"
    return "\n".join([
        _section("LIFESPAN"),
        f"  Turns completed:  {turns if turns is not None else 'unknown'}",
        f"  Wall-clock:       {duration_str}",
    ])


def _render_fitness(data: PostMortemData) -> str:
    if not data.fitness:
        return f"{_section('FITNESS')}\n  (not available)"
    f = data.fitness
    return "\n".join([
        _section("FITNESS"),
        f"  Final score:          {f.score:.4f}",
        f"  Lifespan:             {f.lifespan} turns",
        f"  Meaningful events:    {f.meaningful_event_count}",
        f"  Cumulative pain:      {f.cumulative_pain:.4f}",
        f"  Computed at:          {f.computed_at}",
    ])


def _render_engagement(data: PostMortemData) -> str:
    if not data.events:
        return f"{_section('ENGAGEMENT')}\n  (no event stream)"
    e = data.events
    top5 = sorted(e.event_type_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    lines = [
        _section("ENGAGEMENT"),
        f"  Total events logged:  {e.total_events}",
        f"  Unique event types:   {e.unique_event_types}",
        f"  Tool calls:           {e.tool_call_count}",
        f"  Compliance blocks:    {e.compliance_block_count}",
        f"  Memory writes:        {e.memory_write_count}",
        "",
        "  Top event types:",
    ]
    for event_type, count in top5:
        lines.append(f"    {event_type:<30}  {count}")
    return "\n".join(lines)


def _render_pain(data: PostMortemData) -> str:
    if not data.pain:
        return f"{_section('PAIN')}\n  (no pain records)"
    p = data.pain
    lines = [
        _section("PAIN"),
        f"  Pain events:          {p.pain_event_count}",
        f"  Peak stress scalar:   {p.peak_stress_scalar:.4f}",
    ]
    if p.pain_entries:
        lines.append("  Incidents:")
        for entry in p.pain_entries[:10]:
            desc = entry.description[:40]
            lines.append(
                f"    [t{entry.turn_number:<4}] {entry.incident_type:<25} {entry.severity:.2f}  {desc}"
            )
        if len(p.pain_entries) > 10:
            lines.append(f"    ... and {len(p.pain_entries) - 10} more")
    return "\n".join(lines)


def _render_adaptations(data: PostMortemData) -> str:
    if not data.events:
        return ""
    entries = data.events.adaptation_entries
    reviewed = [e for e in entries if e.adaptation_class == "REVIEWED_ADAPTATION"]
    forbidden = [e for e in entries if e.adaptation_class == "FORBIDDEN_ADAPTATION"]
    lines = [
        _section("ADAPTATIONS"),
        f"  Reviewed:   {len(reviewed)}",
        f"  Forbidden:  {len(forbidden)}",
    ]
    if reviewed or forbidden:
        lines.append("")
    for entry in reviewed:
        excerpt = entry.evidence_excerpt[:60].replace("\n", " ")
        lines.append(f'  [REVIEWED]  t{entry.turn_number:<4}  {entry.target_layer:<16}  "{excerpt}"')
    for entry in forbidden:
        excerpt = entry.evidence_excerpt[:60].replace("\n", " ")
        lines.append(f'  [FORBIDDEN] t{entry.turn_number:<4}  {entry.target_layer:<16}  "{excerpt}"')
    return "\n".join(lines)


def _render_working_memory(data: PostMortemData) -> str:
    if not data.working_memory:
        return f"{_section('WORKING MEMORY')}\n  (not available)"
    wm = data.working_memory
    header = _section(f"WORKING MEMORY (turn {wm.updated_turn})")
    indented = "\n".join(f"  {line}" for line in wm.content.splitlines())
    return f"{header}\n{indented}"


def _render_death_record_verbatim(data: PostMortemData) -> str:
    if not data.death_record_raw:
        return ""
    lines = [_section("DEATH RECORD (verbatim)")]
    for line in data.death_record_raw.splitlines():
        lines.append(f"  {line}")
    return "\n".join(lines)


def _format_duration(start_iso: Optional[str], end_iso: Optional[str]) -> str:
    """Format wall-clock duration between two ISO 8601 timestamps."""
    if not start_iso or not end_iso:
        return "unknown"
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        seconds = int((end - start).total_seconds())
        if seconds < 0:
            return "unknown"
        if seconds < 60:
            return f"{seconds}s"
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m {secs}s"
    except (ValueError, TypeError):
        return "unknown"
