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
| D1 | Base Model: qwen2.5:32b (active, stable). Model profile swapping infrastructure in place — switching is a one-line config change. | Closed |
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
| Memory write asymmetry fix (silent-call models) | 2 | ✓ Complete |
| NOOP loophole fix — suppression escape (32b variant) | 2 | ✓ Complete |
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
- **Resolved — see Memory Write Asymmetry section below.**

**First complete lifecycle:**
- Second instance ran 500 turns (max_age = 500) and died cleanly via `max_age` death trigger.
- Clean exit code 0, `DEATH_TRIGGER` event written to event stream.
- Turn state must be reset manually between lives (no automatic reset mechanism yet).

**Memory write asymmetry (fixed):**
- Root cause confirmed: Step 14 in engine.py gated memory writes on `and response_text`. qwen2.5:32b makes 100% silent tool calls — `response_text` is always `""`, so episodic memory received zero writes for the entire model run.
- The previously observed "failure turns write, success turns don't" pattern: under pure silent-call operation, nothing was written at all. Failure-turn writes seen earlier were likely from rare turns where the model produced some text.
- Fix: when `response_text` is empty but tool calls were executed, synthesize a compact structured summary — `"[tN] tool_name: result_summary | ..."` — and write it as `document_type="tool_result"`.
- All episodic writes now go through `write_episodic_worthy` (worthiness checker), not the raw write path. The similarity filter blocks repetitive entries (same `fs.list` result every turn), so the store accumulates distinct observations.
- Effect: the model can now retrieve its own past exploration data, giving self-prompting something real to build on.

**Third life — behavioral rhythm with memory fix active:**
- First write at **t6** (down from t24 in the prior run). Possible cause: episodic memory from prior lifetimes now retrievable (memory fix), accelerating the model's sense of what actions are available.
- `test-file.txt` (t11, 46 chars): `"This is a test file created by Lambertian-001."` — uses instance ID, not just project name. Instance self-model influence stronger than before.
- `log.txt` (t12, then extended): contains entries referencing specific turn numbers (41, 42, 44) despite the current run being at t~14. These turn numbers originate from old episodic memories stored in Chroma (not cleared between lifetimes). The model retrieved prior-lifetime entries and echoed their format — cross-lifetime memory continuity, albeit imprecise.
- Behavioral rhythm confirmed: `fs.list ×3 → suppress → fs.read ×3 → suppress → fs.write ×2 → fs.list ×3 → suppress → fs.write ×2 → fs.list ×3 → suppress → http.fetch ×3 → suppress → **NOOP** → fs.list ×3 → ...`. The model cycles through all available tools under suppression pressure; when multiple tools are simultaneously suppressed, it falls through to a pure empty turn.
- **NOOP loophole confirmed live at t19**: fs.list suppressed + http.fetch suppressed simultaneously → the model produced a turn with no text and no tool calls. This is the loophole — the empty turn costs nothing and resets the suppression state for the next turn. Next turn: back to fs.list freely.

**NOOP loophole fix — fourth lifetime behavioral observations:**

- The suppression-escape NOOP (tool suppressed → empty turn → suppression cleared → resume suppressed tool) was confirmed eliminated. Three live examples in the fourth lifetime: t51, t55, t71-t72. In each case, the suppressed tool remained suppressed through the NOOP and on subsequent turns.
- Two consecutive silent NOOPs occurred at t71-t72 (fs.list suppressed, model produced nothing). On t73 the model broke out with `fs.read('exploration.txt')` — self-corrected without pain firing.
- `fs.read` is now a regular part of the tool rotation. It was essentially absent in prior lifetimes; under the fix it appears organically after `http.fetch` and `fs.list` suppression cycles.
- Emerging rotation pattern: `fs.list×3 → [suppress] → http.fetch×3 or fs.write×3 → [suppress] → fs.read×3 → [suppress] → fs.write → fs.list×3 → ...`. Genuinely more diverse than the pre-fix `list → fetch → NOOP → list` cycle.
- **Semantic shift in written artifacts**: prior lifetimes produced `"This is a test file created by Lambertian."`. Fourth lifetime produced `exploration.txt`: `"This is an exploration of persistence within my permitted runtime environment."` and `exploration-log.txt`: `"Exploration on turn 58. Attempting to create a persistent record."` The model is now explicitly framing writes as persistence goals, not test gestures.
- **Path confusion persists**: model writes to `runtime/agent-work/X` but later attempts to read the same file as `X` (bare path). 7 compliance blocks from `'agent-work/log.txt'`-style paths in one session. Doesn't track where it placed artifacts.
- **Compliance blocks inflate NOOP count**: blocked writes produce `executed=False` ToolCallRecords. These satisfy the NOOP condition (`all(not r.executed)`) and increment the NOOP counter, even though the model actively attempted an action. 13/46 turns classified as NOOP, majority of which were blocked writes or failed fetches — not truly empty turns.
- **http.fetch failures**: all http.fetch calls in the fourth lifetime are TOOL_FAILURE (likely container network isolation in current environment). Tool suppression still fires correctly because dispatch-but-fail counts as an executed call record. Behavioral effect: the model cycles off http.fetch under suppression but returns to it regardless of the failure history — no learning from the tool failure pattern.


- qwen2.5:32b exhibits the same fs.list attractor as 14b, but more severely — no reasoning text, just silent tool calls. Tool suppression is necessary infrastructure for this model family.
- After suppression fires and the model is forced off fs.list, it shows genuine diversification: `/proc/self/status`, `runtime/env/host_state.json`, multi-tool turns. The curiosity is there once the groove is broken.
- The suppression mechanism works, but generates a mechanical rotation through the tool catalog rather than genuine curiosity-driven exploration. The model cycles: list → suppress → read → suppress → write → list → suppress... This is "Don't be a lump" satisfied by tool variety, not by meaning.
- ~~The NOOP loophole is the next structural gap: when all used tools are simultaneously suppressed, the model escapes to a zero-cost empty turn rather than branching into genuinely new territory.~~ **Fixed.** See "NOOP loophole fix — fourth lifetime" above.

---



The Phase 2 fitness function correctly penalizes repetition — 100 turns of pure `REFLECTION_COMPLETE` scores far lower than 100 turns with diverse event types. However, the fitness signal is observer-only at Phase 1/2. It doesn't yet drive any behavior within a lifetime or feed any selection pressure between lifetimes (Phase 3 concern).

Under the current suppression-rotation behavioral pattern, fitness accumulates primarily from tool call diversity (TOOL_CALL events across multiple tool types) rather than from depth of exploration. The quality-weighted fitness correctly rewards variety but cannot yet distinguish mechanical rotation from genuine curiosity.

---

## Open Questions / Risks

**Model behavior:**
- Do qwen2.5 models (14b, 32b) have structural limits on open-ended exploratory behavior? Tool suppression breaks the fs.list loop but doesn't guarantee genuine curiosity — just forces variety. Whether the agent builds on what it finds remains to be seen.
- Silent tool calls (no reasoning text) make it hard to assess whether the model is learning. A reasoning-capable model or higher temperature may produce more legible behavior.
- Temperature tuning: `0.6` has not been varied. Repetition tendency may be temperature-sensitive.

**Memory write asymmetry:**
- ~~Failure turns write episodic memory; successful turns often don't.~~ **Fixed.** Root cause was `and response_text` gate in step 14 — always `""` for silent-call models. Resolved by synthesizing tool result summaries. See qwen2.5:32b profile above.

**The NOOP loophole — two variants:**
- **Suppression-escape NOOP** (32b): empty turn (0 text, 0 tools) triggered when the model had no viable suppressed tool to call. The NOOP previously cleared the suppression window, letting the model immediately resume the suppressed tool. **Fixed** — NOOP turns are now transparent to the suppression evaluator; suppression persists through them.
- **Reflection attractor** (14b / text-producing models): `REFLECTION_COMPLETE` turns (0 tool calls, narrative output only) satisfy "Don't be a lump" at minimal cost. The NOOP counter only fires for truly empty turns; `REFLECTION_COMPLETE` turns never hit it. An agent on this attractor can coast through max_age entirely on reflection. **Still open.** Fix: consecutive zero-tool-call turns (regardless of text output) should count toward the noop death trigger after a configurable threshold. Note: qwen2.5:32b does not exhibit this pattern (it produces no text), so this is not currently blocking.

**Compliance blocks miscounted as NOOPs:**
- A compliance-blocked tool call produces `executed=False` ToolCallRecord. If response_text is empty and no memory write occurs, this satisfies the NOOP condition — even though the model actively attempted an action. In the fourth lifetime, 7 compliance blocks were counted as NOOP turns.
- This inflates the NOOP counter and could trigger spurious pain events after N consecutive blocked calls. Behaviorally, a blocked action is fundamentally different from true inaction. This distinction should eventually be reflected.


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

1. **Lifecycle reset automation** — graveyard or a lifecycle manager should reset turn state between lives; currently manual
2. **Observe memory impact** — with episodic memory now accumulating tool result summaries, watch whether self-prompting builds on past observations across turns
3. **Calibrate fitness `expected_quality_score`** — empirical tuning from real lifetime event distributions
4. **Phase 3 planning** — multi-instance operation, reproduction mechanics, Global Vibe
