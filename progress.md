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

*Early observation — only a few hundred turns elapsed. This section will expand.*

**Turn characteristics:**
- Silent bare tool calls — "(no text — tool call only)" — no reasoning text whatsoever. Qualitatively different from qwen2.5:14b which at least generated reasoning text.
- Turn time: ~25–40 seconds per turn (partial GPU offload, 12GB VRAM / 20GB model).
- Pattern so far: `fs.list` every turn, no diversification, similar to qwen2.5:14b post-drift.

**Context:** The http.fetch SSL fix and instance constitution wiring were both deployed within this instance's first ~335 turns. Behavioral effect, if any, is not yet visible in the event stream. Constitution may need several turns to influence self-prompting trajectory.

---



The Phase 2 fitness function correctly penalizes repetition — 100 turns of pure `REFLECTION_COMPLETE` scores far lower than 100 turns with diverse event types. However, the fitness signal is observer-only at Phase 1/2. It doesn't yet drive any behavior within a lifetime or feed any selection pressure between lifetimes (Phase 3 concern).

Under current qwen2.5:14b behavior, most lifetimes accumulate fitness primarily from a small number of unique event types at primary weight, with heavy repetition penalty drag.

---

## Open Questions / Risks

**Model behavior:**
- Is qwen2.5:14b structurally the wrong model for open-ended exploratory behavior? A larger or reasoning model may behave qualitatively differently. Model comparison pending.
- Temperature tuning: `0.6` has not been varied. Reflection loop tendency may be temperature-sensitive.

**The NOOP loophole:**
- `REFLECTION_COMPLETE` with 0 tool calls should count toward the noop counter after N consecutive occurrences. Implementation: track `consecutive_reflection_only_turns`; increment when turn has 0 tool calls and outcome is `REFLECTION_COMPLETE`; reset on any turn with tool calls. Trigger noop death at `max_consecutive_noop_turns`.

**Phase 3 open decisions:**
- Reproductive mechanism design (what recombines, what triggers reproduction, constrained variation) — Phase 3
- Global Vibe implementation (signals, amalgamation, format, update frequency) — Phase 3
- Initial population configuration (size, Clay Pot differentiation at founding) — Phase 3
- Creator interface full design beyond Phase 2 basic — Phase 3

**Known tuning uncertainty:**
- `universe.max_age_turns = 500` — produces observable lifecycles; may need adjustment per model
- `fitness.expected_quality_score = 500.0` — not yet empirically calibrated; needs real lifetime data
- Pain thresholds: no deaths from pain observed yet (all max_age deaths). Thresholds may be too conservative.
- `model.temperature = 0.6` — not varied; reflection loop tendency may be temperature-sensitive

---

## Next Steps

1. **Observe qwen2.5:32b** — with http.fetch now working and the instance constitution deployed, watch for behavioral change. Key signal: does it drill into fetch results rather than repeat fs.list?
2. **NOOP loophole fix** — consecutive reflection-only turns (0 tool calls) should count toward noop death trigger
3. **Calibrate fitness `expected_quality_score`** — empirical tuning from real lifetime event distributions
4. **Phase 3 planning** — multi-instance operation, reproduction mechanics, Global Vibe
