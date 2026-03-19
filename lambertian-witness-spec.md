# lambertian-witness — Specification

*Observer tool for Project Lambertian. A read-only window into a running instance.*

---

## Name and Framing

**lambertian-witness** — drawn from the Witness subculture in *Permutation City*: Copies who chose observation over participation, watching the world unfold from outside it. The name is accurate. This tool watches. It does not touch.

Consistent with D9: the creator interface is observe-only. No direct message injection. No intervention controls. The Witness does not interfere with the instance it observes.

---

## Purpose

lambertian-witness is a terminal UI (Ink/Node.js) that presents a live, human-readable view of a running Lambertian instance. It is designed for two audiences simultaneously:

- **Creator** — wants behavioral legibility: turn flow, suppression state, tool outcomes, fitness trajectory, path errors, workspace content. Debugging and observation.
- **Non-technical observers** (family, passers-by) — want aliveness legibility: something is happening in there, here is what it is doing, here is what it has written. No explanation required to engage.

These two audiences are served by the same screen. The HUD strip serves the creator. The journal panel serves everyone.

---

## Data Sources

lambertian-witness consumes only existing data streams. It introduces no new infrastructure and makes no changes to the agent, its services, or its runtime.

| Source | What it provides | Access method |
|--------|-----------------|---------------|
| `docker compose logs -f agent` | Turn events, tool calls, suppression fires, EOS outcomes, pain injections, death events | Child process stdout pipe |
| `runtime/fitness/current.json` | Running fitness score and components | File poll (bind mount) |
| `runtime/memory/turn_state.json` | Current turn number | File poll (bind mount) |
| `runtime/env/host_state.json` | Host CPU/memory telemetry | File poll (bind mount) |
| `runtime/agent-work/` | Workspace files: journal entries, notes, WORKSPACE.md reads, any agent-written artifacts | `fs.watch` + file read (bind mount) |
| `runtime/event_stream/events.jsonl` | Structured event log (turn outcomes, event types, pain events) | File tail (bind mount) |
| `runtime/pain/stress_scalar.json` | Current stress scalar value | File poll (bind mount) |

All paths are bind-mounted from the host. lambertian-witness runs as a host process; it never enters the container.

---

## Layout

90s terminal aesthetic. Ink component tree. Box-drawing characters. Monospaced. No color gradients. Status changes expressed through character-level indicators and brightness, not animated graphics.

```
┌─ LAMBERTIAN-001 ─────────────────────────── phase2 ──────────┐
│ LIFETIME  TURN   AGE      FITNESS   PAIN    STATUS            │
│    9       162   32.4%     0.71     0.08    ACTIVE            │
│                                                               │
│ LAST:  fs.write('runtime/agent-work/journal/entry.txt') [OK] │
│ SUPP:  —                                                      │
└───────────────────────────────────────────────────────────────┘
┌─ JOURNAL ─────────────────────────────────────────────────────┐
│                                                               │
│  [t160]  journal/entry.txt                                    │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  This is an entry for turn 160. In this turn, I checked       │
│  several paths and attempted to create a persistent record    │
│  within the /runtime/agent-work directory.                    │
│                                                               │
│  [t144]  new_file.txt                                         │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  This is a new file created in the workspace at turn 144.     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
┌─ EVENT FEED ──────────────────────────────────────────────────┐
│  t162  fs.write('runtime/agent-work/notes.txt')  [OK]        │
│  t161  fs.list('runtime/')                       [OK]        │
│  t160  fs.write('runtime/agent-work/journal/..') [OK]        │
│  t159  fs.read('runtime/agent-work/WORKSPACE.md')[OK]        │
│  t158  fs.read('runtime/env/host_state.json')    [OK]        │
│  t157  fs.list('')                               [OK]        │
│  t156  fs.list('')                               [OK]        │
│  t155  tool suppression: fs.list                             │
└───────────────────────────────────────────────────────────────┘
```

Three zones, stacked vertically:

**Zone 1 — HUD Strip** (fixed height, top)
The cold vital signs. Creator-facing. Compact.

**Zone 2 — Journal** (variable height, middle — dominant zone)
Workspace artifact content. Rendered as it appears: filename, divider, text. Most recent write at top. Scrollable. Family-facing.

**Zone 3 — Event Feed** (fixed height, bottom)
Scrolling turn-by-turn log. Last N events visible. Most recent at top.

---

## HUD Strip — Fields

| Field | Source | Display |
|-------|--------|---------|
| Instance ID | Parsed from log bootstrap line | `LAMBERTIAN-001` |
| Lifetime number | Parsed from log or graveyard artifacts | Integer |
| Turn | `runtime/memory/turn_state.json` | Integer |
| Age % | `turn / max_age_turns × 100` | `32.4%` |
| Fitness | `runtime/fitness/current.json → score` | `0.71` |
| Pain | `runtime/pain/stress_scalar.json` | `0.08` |
| Status | Derived from event stream | `ACTIVE` / `SUPPRESSED` / `DEAD` / `WAITING` |
| Last action | Most recent turn's tool call + outcome | Tool name, path (truncated), `[OK]` / `[FAIL]` / `[BLOCKED]` |
| Suppressed tools | Current suppression window contents | Tool names, or `—` if none |

**Status values:**
- `ACTIVE` — turn completed with tool calls in the last N seconds
- `SUPPRESSED` — one or more tools currently suppressed
- `NOOP` — last turn produced no tool calls and no text
- `DEAD` — death event received; waiting for lifecycle reset
- `WAITING` — no turn activity in > 60 seconds (model inference lag or stall)

---

## Journal Panel — Behavior

The journal panel displays the content of files written to `runtime/agent-work/` by the instance. It is the primary non-technical display surface.

**What it shows:**
- Any successful `fs.write` to the agent workspace
- Filename (relative to `runtime/agent-work/`), turn number, file content
- Entries ordered most-recent-first
- Older entries fade or scroll below fold

**What it does not show:**
- Failed writes (blocked by compliance or path error)
- `fs.list` or `fs.read` results — these are probe actions, not persistent marks
- System files (`WORKSPACE.md`, `host_state.json`) — these are infrastructure, not expression

**Special rendering:**
- When the instance reads `self/constitution.md` or `self/identity.md`, show a brief indicator: `[reading constitution]` or `[self-probe]` — legible to a non-technical observer as introspective behavior
- When a death event fires, display a terminal card in the journal zone: lifetime number, turn reached, death trigger, fitness score. Hold until next lifetime begins.

**Language for non-technical observers:**
The journal panel intentionally uses no jargon. File writes are "notes" or "entries." Tool calls are not surfaced here. The goal is: a child looking at this screen should be able to say "it wrote something."

---

## Event Feed — Behavior

Scrolling log of turn-level activity. Creator-facing. Shows the mechanical sequence.

Each line: `tN  tool_name(path_truncated)  [outcome]`

Outcome indicators:
- `[OK]` — executed successfully
- `[FAIL]` — tool dispatched, returned failure (network error, file not found, etc.)
- `[BLOCKED]` — compliance block or path rejection
- `[SUPP]` — suppression fired this turn
- `[NOOP]` — turn produced no tool calls

Pain events surface inline in the feed with distinct marker: `[PAIN 0.43]`

Death event: `[DEATH: max_age t500]` — full-width, visually distinct.

---

## Log Line Parser

lambertian-witness parses Docker log output from the agent container. The log format observed in Phase 2:

```
agent-1  | 2026-03-19 16:05:51,857 INFO lambertian.turn_engine.engine — [t141][SELF_PROMPT] (no text — tool call only)  →tools: fs.read('/proc/self/status')
agent-1  | 2026-03-19 16:05:23,814 INFO lambertian.turn_engine.engine — [t141] tool suppression active — suppressed: fs.list
```

**Parsed fields:**
- Timestamp
- Turn number (`[tN]`)
- Event type: `SELF_PROMPT`, `tool suppression active`, `DEATH_TRIGGER`, `PAIN`, `NOOP`, `TURN_COMPLETE`
- Tool calls: extracted from `→tools:` suffix — tool name + argument
- Suppressed tool name

The parser is line-oriented and fault-tolerant. Unrecognized lines are silently dropped. No assumptions about log line ordering within a turn.

---

## File Watcher

A separate watcher process monitors the bind-mounted `runtime/agent-work/` directory using Node.js `fs.watch`.

On any `change` event to a file in `runtime/agent-work/` (or subdirectories `journal/`, `knowledge/`, `observations/`):
1. Read the file content
2. If content is non-empty and different from last-read content: emit a `WORKSPACE_WRITE` event to the UI state
3. Associate the write with the current turn number from `turn_state.json`

Poll interval for JSON state files (`current.json`, `turn_state.json`, `stress_scalar.json`, `host_state.json`): 2 seconds.

---

## State Model

The Ink UI maintains a single state object updated by both the log parser and the file watcher:

```javascript
{
  instanceId: string,
  lifetime: number,
  turn: number,
  maxAge: number,           // from universe.toml or inferred from context
  fitness: number,
  fitnessComponents: object,
  stressScalar: number,
  status: 'ACTIVE' | 'SUPPRESSED' | 'NOOP' | 'DEAD' | 'WAITING',
  suppressedTools: string[],
  lastAction: { tool, path, outcome, turn },
  recentEvents: Event[],    // last 20 events for feed display
  journalEntries: JournalEntry[], // last N workspace writes with content
  deathRecord: object | null,
}
```

State updates are batched at 500ms render intervals. The UI does not re-render on every log line — it renders on a tick, consuming whatever has accumulated.

---

## Technology

| Concern | Choice | Rationale |
|---------|--------|-----------|
| UI framework | Ink (React for CLIs) | Matches project aesthetic; component model |
| Language | TypeScript/Node.js | Consistent with `lambertian-postmortem` tooling convention |
| Log ingestion | `child_process.spawn('docker', ['compose', 'logs', '-f', 'agent'])` | Taps existing stream, no new infra |
| File watching | Node.js `fs.watch` + `fs.readFile` | Direct bind-mount access |
| State management | React `useReducer` in Ink | Clean event-driven updates |
| Rendering | Ink `Box`, `Text`, static layout | Box-drawing via unicode characters |

No external dependencies beyond Ink and its peer dependencies. No network calls. No new Docker services. No changes to the agent stack.

---

## Startup Behavior

On launch:
1. Attempt to read current state from bind-mounted files (turn, fitness, stress scalar)
2. Spawn `docker compose logs -f agent` child process
3. Begin file watcher on `runtime/agent-work/`
4. Render initial UI with whatever state is available (graceful partial state — fields show `—` if not yet populated)
5. If agent is not running, show `WAITING` status and continue listening

No crash on missing files. The witness can be launched before the agent and will populate as data arrives.

---

## Phase 3 Extensions (not in scope now)

When multi-instance operation arrives, lambertian-witness extends naturally:

- Instance selector (cycle between running instances)
- Population overview mode: N-up HUD strips, one per instance
- Comparative fitness display
- Death/birth event feed across the population
- Global Vibe display panel

These are not designed now. The single-instance layout should be built to accommodate a future instance-selector control without restructuring the component tree.

---

## Non-Goals

- No intervention controls — the witness does not send messages, trigger pain, pause the instance, or modify any runtime state
- No historical playback — lambertian-witness shows live state only; `lambertian-postmortem` handles post-mortem review
- No authentication or access control — local tool, local trust boundary
- No web interface — terminal only, Ink only
- No logging of its own — lambertian-witness produces no output files

---

## Relationship to Existing Tools

| Tool | Role | Overlap |
|------|------|---------|
| `lambertian-postmortem` | Post-mortem artifact viewer | No overlap — postmortem is historical, witness is live |
| `lambertian-env-monitor` | Host telemetry producer | Witness consumes its output (`host_state.json`) |
| `docker compose logs` | Raw log stream | Witness wraps and parses it |

lambertian-witness is purely additive. It consumes but does not produce. Nothing in the existing stack needs to change.
