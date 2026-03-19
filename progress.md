# Project Lambertian — Progress

*Living implementation tracker. Not philosophy. Not spec. Just what's true right now.*

---

## Current Status

**Phase:** Phase 2 (single-instance, running)

**Branch:** `phase2`

**Overall:** Phase 1 and Phase 2 are complete and deployed. A single Lambertian instance is running under Phase 2 conditions with qwen2.5:14b. Model-specific behavioral patterns have been characterized (see observations below). Model profile swapping infrastructure is in progress.

**Running services:**
- `agent` — turn engine, EOS compliance, MCP gateway, memory, self-model (qwen2.5:14b via Ollama)
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
| Model profile swapping infrastructure | 2 | In progress |
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

### Quality-Weighted Fitness

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

1. **Model profile swapping** (in progress) — formalize model profiles in `universe.toml` and `loader.py` so switching models is a one-line config change
2. **Run with alternative models** — compare qwen2.5:32b, llama3.1:70b, phi4 against qwen2.5:14b for exploratory behavior
3. **NOOP loophole fix** — consecutive reflection-only turns (0 tool calls) should count toward noop death trigger
4. **Calibrate fitness `expected_quality_score`** — empirical tuning from real lifetime event distributions
5. **Phase 3 planning** — multi-instance operation, reproduction mechanics, Global Vibe
