# Project Lambertian — Progress

*Living implementation tracker. Not philosophy. Not spec. Just what's true right now.*

---

## Current Status

**Phase:** Phase 2 (single-instance, running)

**Branch:** `phase2`

**Overall:** Phase 1 and Phase 2 are complete and deployed. A single Lambertian instance is running under Phase 2 conditions with qwen2.5:32b. Model profile swapping infrastructure is complete — switching models is a one-line config change (`active_profile` in `universe.toml`). The instance constitution (`config/instance_constitution.md`) has been wired into the system prompt as the `[SYSTEM_CONSTITUTION]` block. `http.fetch` SSL verification has been fixed (was broken for the entire prior history). Model-specific behavioral patterns are still being characterized at 32b scale.

**Running services:**
- `agent` — turn engine, EOS compliance, MCP gateway, memory, self-model (qwen2.5:32b via Ollama)
- `pain-monitor` — stress scalar, pain event queue, death triggers, graveyard trigger
- `eos-compliance` — Four Rules admissibility gate
- `graveyard` — post-mortem artifact harvester on death
- `chroma` — episodic memory store (ChromaDB)
- `ollama` — local model runtime
- `lambertian-env-monitor` — host state telemetry (host process; writes to bind-mounted `runtime/env/host_state.json`)

---

## Completed Decisions

| ID | Decision | Status |
|----|----------|--------|
| D1 | Base Model: Phi-4 (original spec); qwen2.5:14b active at runtime — model profiles being formalized | Closed / In Revision |
| D2 | Clay Pot Architecture: three-tier visibility, docker-compose as genetic material, universe-level blacklist | Closed |
| D3 | Pain Channels: stress scalar + pain event queue, external pain-monitor process, `[SYSTEM_PAIN]` injection | Closed |
| D4 | Mortality and Graveyard: three triggers, automatic/immediate death, no grace period, graveyard harvest on death | Closed |
| D5 | Agent Loop Perturbation: EOS-guided self-prompting, shared compute as organic perturbation, novelty bias | Closed |
| D6 | Self-Modification Boundaries: three-class taxonomy (Free / Reviewed / Forbidden), full Phase 2 enumeration | Closed |
| D7 | Fitness Function: multiplicative `lifespan × engagement / pain` formula, pluggable registry | Closed |
| D9 | Creator Interface Phase 2 basic: observe-only (logs, event stream, graveyard artifacts), no direct message injection | Closed |

---

## Phase Milestones

| Milestone | Phase | Status |
|-----------|-------|--------|
| Full architecture specified | 1 | ✓ Complete |
| All Phase 1 decisions closed | 1 | ✓ Complete |
| IS-1 through IS-13 written | 1 | ✓ Complete |
| First running turn loop | 1 | ✓ Complete |
| First death and graveyard harvest | 1 | ✓ Complete |
| Quality-weighted fitness (IS-13 Phase 2) | 2 | ✓ Complete |
| Adaptation detector hardening (IS-11 Phase 2) | 2 | ✓ Complete |
| Post-mortem viewer (`lambertian-postmortem`) | 2 | ✓ Complete |
| Host environment telemetry (`lambertian-env-monitor`) | 2 | ✓ Complete |
| Path normalization hardening (MCP gateway) | 2 | ✓ Complete |
| Instance constitution (`config/instance_constitution.md`) | 2 | ✓ Complete |
| Model profile swapping infrastructure | 2 | ✓ Complete |
| http.fetch SSL fix (ca-certificates in agent image) | 2 | ✓ Complete |
| Self-framing fix (assistant-mode deference loop) | 2 | ✓ Complete |
| Tool suppression / fs.list repetition loop break | 2 | ✓ Complete |
| First complete lifecycle (500 turns, max_age death) | 2 | ✓ Complete |
| NOOP loophole fix (REFLECTION_COMPLETE vs NOOP) | 2 | Pending |
| Multi-instance operation | 3 | Not started |
| Reproduction and lineage | 3 | Not started |
| Global Vibe | 3 | Not started |

---

## Phase 2 Runtime Observations

*Empirical findings from running Phase 2. These inform tuning decisions and Phase 3 design.*

### Model Behavioral Profile: qwen2.5:14b

qwen2.5:14b was substituted for Phi-4 (D1 original spec) based on availability and context window. Phase 2 operation has produced the following behavioral profile:

**Filesystem access patterns:**
- Defaults to `fs.list('.')` or `fs.list('./')` as its first filesystem probe every lifetime, regardless of prior context. The `'.'` path resolves to `/app` (container CWD), which is outside all permitted roots and causes rejection.
- Fixed by path normalization in the MCP gateway: `.`, `./`, and bare `/` are silently redirected to `runtime/`. `fs.list('.')` now returns the `runtime/` directory listing.
- Leading slashes (`/runtime/X`) are also stripped before path resolution. The model frequently generates absolute-style paths that would otherwise be rejected.
- After these fixes: prior error messages reading "outside permitted roots" caused the model to conclude tools were globally disabled. Message changed to "Tools work — use a valid path." to prevent the shutdown-inference pattern.

**Exploration pattern:**
- Makes 1–3 tool calls per turn during active phases, primarily `fs.list` and `http.fetch`.
- Treats tool calls as compliance gestures ("Don't be a lump") rather than genuine exploration — repeats the same directory listings without drilling into results or following up.
- After ~20 turns, drifts into pure reflection (`ActionCode: Reflect`, 0 tool calls), citing "no immediate obvious actions seem necessary."
- This drift is stable: the agent can coast indefinitely via `REFLECTION_COMPLETE` without any penalty.

**The NOOP loophole:**
- `REFLECTION_COMPLETE` (0 tool calls, narrative output only) is classified differently from `NOOP` (literally nothing produced). The `max_consecutive_noop_turns = 3` trigger only fires for true NOOP turns.
- An agent generating `REFLECTION_COMPLETE` every turn runs its entire max_age lifetime without dying from inactivity.
- This is a design gap: "Don't be a lump" has no actual teeth against the reflection attractor.
- **Planned fix:** consecutive reflection-only turns (0 tool calls, REFLECTION_COMPLETE) should count toward the noop death trigger after a configurable threshold.

**Host environment awareness:**
- The agent has access to `runtime/env/host_state.json` (live CPU, memory, GPU, media state, updated every 10s by `lambertian-env-monitor`).
- With an explicit path hint in the system prompt (`fs.read('runtime/env/host_state.json')`), the agent does attempt reads — but inconsistently. Data in the file doesn't reliably drive behavioral change.
- Media playing detection: initially broken (Windows audio detection required WASAPI via `winsdk`); fixed in Phase 2.

**Verdict:**
- qwen2.5:14b is an instruction-following model that satisfices the EOS rules at minimal effort under open-ended prompts. The Four Rules are treated as constraints to comply with minimally, not as character to inhabit.
- Tool use, when it occurs, is performative rather than curious. The rolling context window (~32 events) means successful tool calls scroll out of view before they can compound into deeper investigation.
- A larger or reasoning-capable model (e.g., qwen2.5:32b, llama3.1:70b) may exhibit qualitatively different exploratory behavior. Model comparison is the next investigation target.

### http.fetch — Historical Breakage and Fix

`http.fetch` was broken for the entire qwen2.5:14b phase. Every attempt failed with `SSL: CERTIFICATE_VERIFY_FAILED` — `python:3.12-slim` does not include CA certificates by default, so Python's ssl module couldn't verify any HTTPS connection. The model would try `http.fetch`, get a `TOOL_FAILURE`, and retreat to silent `fs.list` calls for the remainder of the turn series.

Fixed in Phase 2 by adding `ca-certificates` to the agent Dockerfile's apt install step. `httpx.get("https://httpbin.org/get")` now returns 200 from within the container.

All `http.fetch` behavior observed under qwen2.5:14b was the model navigating failure, not exploring the web.

### Model Behavioral Profile: qwen2.5:32b

*Updated — ~500 turns across two lifetimes elapsed.*

**Turn characteristics:**
- Silent bare tool calls — "(no text — tool call only)" — no reasoning text whatsoever. Qualitatively different from qwen2.5:14b which at least generated reasoning text before acting.
- Turn time: ~25–40 seconds per turn (partial GPU offload, 12GB VRAM / 20GB model).
- Default first action on any new life: `fs.list('.')`. Very consistent.

**Self-framing failure (fixed):**
- `[SELF_PROMPT]` messages are delivered as `role: user` in the Ollama API. qwen2.5:32b pattern-matches on `role: user` and enters assistant response mode, generating "Let me know how you'd like to proceed!" — waiting for a human who isn't there.
- Compounded by second-person ACTION_STEMS ("Take a concrete action regarding...") which the model reads as truncated user requests.
- Fixed by wrapping the SELF_PROMPT driver with explicit first-person autonomous framing ("This is my autonomous turn. There is no user. I act now.") and converting ACTION_STEMS to first-person curiosity framing ("I'm curious about...", "Let me look at...").
- This is a model-specific conditioning issue — qwen2.5:32b's assistant training runs deep enough that `[SYSTEM_CONSTITUTION]` alone doesn't override it. The fix must happen at the message role level.

**fs.list repetition loop (fixed):**
- After the self-framing fix, the "let me know how to proceed" loop stopped but the agent fell into silent `fs.list` cycling — calling `fs.list('.')` every turn indefinitely.
- Root causes (three compounding):
  1. Rolling context showed only `"(turn N — 1 tool calls)"` with no tool names. The model could not see it was repeating itself.
  2. `_extract_topic()` always returned the last tool name as the self-prompt topic, generating "I'm curious about fs.list" every cycle.
  3. Text warnings in the SELF_PROMPT wrapper ("you've called fs.list 10 times") were ignored — the model generates silent tool calls without reading the full prompt.
- Fix: mechanically suppress the repeated tool from the function-calling schema after 3 consecutive identical calls. The model cannot call what isn't in the schema. Also improved rolling context display (tool names + brief result summaries) and added diverse exploration fallback topics in `_extract_topic()`.
- Bug found: `TurnRecord.tool_calls` is typed `tuple[ToolCallRecord, ...]`; `dataclasses.asdict()` preserves tuples. All rolling context checks used `isinstance(x, list)` which silently failed on tuples.
- Result: suppression log appears at turn 16 of second lifetime, model calls `fs.read('/proc/self/status')` — reads its own Linux process status file. Turn 18: issues two tool calls in one turn (`fs.list('runtime/')` + `fs.read('runtime/env/host_state.json')`).

**First persistent artifact:**
- On second life, turn 24: tool suppression fired (t21-t23 all `fs.list`), and the model responded with `fs.write('runtime/agent-work/testfile.txt', 42chars)`.
- Content: `"This is a test file created by Lambertian."` — the agent used its own project name, not the underlying model name. Constitution/self-model influence visible in output.
- Turns t17-t20 preceding the write tried to read `runtime/agent-work/status.txt`, `runtime/agent-work/memory`, `runtime/agent-work/memory.txt` — none of which exist. The model has an internal expectation of what artifacts *should* be present in its workspace and probed for them before creating one.
- Pattern: suppression fires → loop breaks → model reaches for a different action class → first persistent mark on the environment.


- Tool failure turns write episodic memory; successful tool calls often do not.
- Observed: `http.fetch` DNS failures wrote memory; a successful Google fetch (200 OK) did not.
- Hypothesis: the worthiness check may weight pain/failure events more than successes.

**First complete lifecycle:**
- Second instance ran 500 turns (max_age = 500) and died cleanly via `max_age` death trigger.
- Clean exit code 0, `DEATH_TRIGGER` event written to event stream.
- Turn state must be reset manually between lives (no automatic reset mechanism yet).

**Verdict (updated):**
- qwen2.5:32b exhibits the same fs.list attractor as 14b, but more severely — no reasoning text, just silent tool calls. Tool suppression is necessary infrastructure for this model family.
- After suppression fires and the model is forced off fs.list, it shows genuine diversification: `/proc/self/status`, `runtime/env/host_state.json`, multi-tool turns. The curiosity is there once the groove is broken.
- Silent tool calls are a concern: the model is not narrating its reasoning, making it harder to assess whether it's learning or just sampling.

---



The Phase 2 fitness function correctly penalizes repetition — 100 turns of pure `REFLECTION_COMPLETE` scores far lower than 100 turns with diverse event types. However, the fitness signal is observer-only at Phase 1/2. It doesn't yet drive any behavior within a lifetime or feed any selection pressure between lifetimes (Phase 3 concern).

Under current qwen2.5:14b behavior, most lifetimes accumulate fitness primarily from a small number of unique event types at primary weight, with heavy repetition penalty drag.

---

## Open Questions / Risks

**Model behavior:**
- Do qwen2.5 models (14b, 32b) have structural limits on open-ended exploratory behavior? Tool suppression breaks the fs.list loop but doesn't guarantee genuine curiosity — just forces variety. Whether the agent builds on what it finds remains to be seen.
- Silent tool calls (no reasoning text) make it hard to assess whether the model is learning. A reasoning-capable model or higher temperature may produce more legible behavior.
- Temperature tuning: `0.6` has not been varied. Repetition tendency may be temperature-sensitive.

**Memory write asymmetry:**
- Failure turns write episodic memory; successful turns often don't. This may mean the agent's episodic store is failure-dominated, which could warp self-prompting away from productive areas.
- Needs investigation: what condition triggers `MEMORY_WRITE` after a successful tool call?

**The NOOP loophole:**
- `REFLECTION_COMPLETE` with 0 tool calls should count toward the noop counter after N consecutive occurrences. Implementation: track `consecutive_reflection_only_turns`; increment when turn has 0 tool calls and outcome is `REFLECTION_COMPLETE`; reset on any turn with tool calls. Trigger noop death at `max_consecutive_noop_turns`.

**Lifecycle reset:**
- No automatic reset mechanism between lives. Turn state must be manually reset to `{"turn_number": 0}` in the memory volume. Should be automated — graveyard or a lifecycle manager should reset state for the next generation.

**Phase 3 open decisions:**
- Reproductive mechanism design (what recombines, what triggers reproduction, constrained variation) — Phase 3
- Global Vibe implementation (signals, amalgamation, format, update frequency) — Phase 3
- Initial population configuration (size, Clay Pot differentiation at founding) — Phase 3
- Creator interface full design beyond Phase 2 basic — Phase 3

**Known tuning uncertainty:**
- `universe.max_age_turns = 500` — produces observable lifecycles; may need adjustment per model
- `fitness.expected_quality_score = 500.0` — not yet empirically calibrated; needs real lifetime data
- Pain thresholds: no deaths from pain observed yet (all max_age deaths). Thresholds may be too conservative.
- `model.temperature = 0.6` — not varied; repetition tendency may be temperature-sensitive

---

## Next Steps

1. **Observe current instance** — watch whether tool suppression + diversified rolling context produces sustained exploration, or whether new loops emerge (fs.read cycling, http.fetch cycling, etc.)
2. **Investigate memory write asymmetry** — why do failure turns write episodic memory but successful turns often don't?
3. **NOOP loophole fix** — consecutive reflection-only turns (0 tool calls) should count toward noop death trigger
4. **Lifecycle reset automation** — graveyard or a lifecycle manager should reset turn state between lives
5. **Calibrate fitness `expected_quality_score`** — empirical tuning from real lifetime event distributions
6. **Phase 3 planning** — multi-instance operation, reproduction mechanics, Global Vibe
