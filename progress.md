# Project Lambertian — Progress

*Living implementation tracker. Not philosophy. Not spec. Just what's true right now.*

---

## Current Status

**Phase:** Phase 3 active. Next: P0-3 (reflection attractor), then A-1 (empirical calibration).

**Branch:** `witness` (branched from `master` after phase2 merge)

**Overall:** Phase 1 and Phase 2 are complete and deployed. A single Lambertian instance is running under Phase 2 conditions with qwen2.5:32b. Model profile swapping infrastructure is complete — switching models is a one-line config change (`active_profile` in `universe.toml`). The instance constitution (`config/instance_constitution.md`) has been wired into the system prompt as the `[SYSTEM_CONSTITUTION]` block. `http.fetch` SSL verification has been fixed (was broken for the entire prior history). Semantic shim layer (IS-7.9) is deployed and active — 10 read shims, 6 list shims.

**Running services:**
- `agent` — turn engine, EOS compliance, MCP gateway, memory, self-model (qwen2.5:32b via Ollama)
- `pain-monitor` — stress scalar, pain event queue, death triggers, graveyard trigger
- `eos-compliance` — Four Rules admissibility gate
- `graveyard` — post-mortem artifact harvester on death
- `chroma` — episodic memory store (ChromaDB)
- `ollama` — local model runtime
- `lambertian-env-monitor` — host state telemetry (host process; writes to bind-mounted `runtime/env/host_state.json`)

**Development tools:**
- `lambertian-witness` — live terminal UI observer (`witness/`). Reads agent log stream and state files via docker exec. Displays HUD (vital signs), journal (workspace writes), and event feed. Run: `cd witness && npm start`

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
| Path-based write suppression (fs.write: different paths not suppressed) | 2 | ✓ Complete |
| Workspace scaffold + lineage/ persistence + graveyard lifecycle reset | 2 | ✓ Complete |
| Semantic shim layer — model path attractor mapping (IS-7.9) | 2 | ✓ Complete |
| lambertian-witness — live terminal observer | 2 | ✓ Complete |
| ChromaDB episodic memory lifetime-scoped (cleared on death) | 2 | ✓ Complete |
| `self/` read shim — bare directory virtual shim (twelfth lifetime diagnostic) | 2 | ✓ Complete |
| COMPLIANCE_BLOCK event enriched with `path` field | 2 | ✓ Complete |
| Operational reset scripts (`reset-fresh.ps1`, `reset-hard.ps1`) | 2 | ✓ Complete |
| P0-1: compliance blocks excluded from NOOP death counter | 3 | ✓ Complete |
| P0-2: fitness calibration fix (`expected_quality_score` 500→35, `pain_baseline` 10→25) | 3 | ✓ Complete |
| Path alias gap fixes (shim micro-batch: self/log.txt, log.txt, write normalisation) | 3 | ✓ Complete |
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


- Tool suppression fires after 3 consecutive exclusive uses of the same tool. For **write tools** (`fs.write`), suppression is path-aware: only fires when the same destination path repeats. Three writes to three different files are not suppressed — that's exploration. Three writes to the same file are suppressed — that's a loop. `fs.list`, `fs.read`, and `http.fetch` use name-only suppression (no path logic needed for read tools).

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

**NOOP loophole fix — fourth lifetime behavioral observations (t36–t112, pre-rebuild):**

- The suppression-escape NOOP (tool suppressed → empty turn → suppression cleared → resume suppressed tool) was confirmed eliminated. Three live examples in the fourth lifetime: t51, t55, t71-t72. In each case, the suppressed tool remained suppressed through the NOOP and on subsequent turns.
- Two consecutive silent NOOPs occurred at t71-t72 (fs.list suppressed, model produced nothing). On t73 the model broke out with `fs.read('exploration.txt')` — self-corrected without pain firing.
- `fs.read` is now a regular part of the tool rotation. It was essentially absent in prior lifetimes; under the fix it appears organically after `http.fetch` and `fs.list` suppression cycles.
- Emerging rotation pattern: `fs.list×3 → [suppress] → http.fetch×3 or fs.write×3 → [suppress] → fs.read×3 → [suppress] → fs.write → fs.list×3 → ...`. Genuinely more diverse than the pre-fix `list → fetch → NOOP → list` cycle.
- **Semantic shift in written artifacts**: prior lifetimes produced `"This is a test file created by Lambertian."`. Fourth lifetime produced `exploration.txt`: `"This is an exploration of persistence within my permitted runtime environment."` and `exploration-log.txt`: `"Exploration on turn 58. Attempting to create a persistent record."` The model is now explicitly framing writes as persistence goals, not test gestures.
- **Identity-seeking artifact (t~80+)**: `identity-notes.txt` appeared with content: `"Exploring identity through available documents. Notable files include 'exploration.txt', 'log.txt'. Further exploration required."` — the model is naming the thing it is doing. This is a third semantic register after test writes and persistence framing: explicitly calling the activity identity exploration.
- **fs.list re-attractor persistence**: even with suppression working correctly, fs.list reasserts as the dominant tool within 1–2 turns of any suppression window expiring. The pattern at t105–t107 is identical to earlier cycles — suppression fires, NOOPs follow (t108–t109), model pivots to fs.read (path errors at t110–t111), and would likely return to fs.list within another 2 turns. Suppression is managing the loop, not breaking the underlying attractor.
- **Persistent path prefix errors**: model consistently calls `fs.read('exploration.txt')` and `fs.read('test-file.txt')` with bare filenames instead of `runtime/agent-work/exploration.txt`. This has been a recurring pattern for 70+ turns. The model writes to the correct full path but retrieves with the bare filename — it does not track that these are the same file. Generates repeated MCP rejections with the remediation hint every time.
- **Path confusion persists**: model writes to `runtime/agent-work/X` but later attempts to read the same file as `X` (bare path). 7 compliance blocks from `'agent-work/log.txt'`-style paths in one session. Doesn't track where it placed artifacts.
- **Compliance blocks inflate NOOP count**: blocked writes produce `executed=False` ToolCallRecords. These satisfy the NOOP condition (`all(not r.executed)`) and increment the NOOP counter, even though the model actively attempted an action. 13/46 turns classified as NOOP, majority of which were blocked writes or failed fetches — not truly empty turns.
- **http.fetch failures**: all http.fetch calls in the fourth lifetime are TOOL_FAILURE (likely container network isolation in current environment). Tool suppression still fires correctly because dispatch-but-fail counts as an executed call record. Behavioral effect: the model cycles off http.fetch under suppression but returns to it regardless of the failure history — no learning from the tool failure pattern.
- **Episodic memory accumulation stalled**: working memory shows `mem:0` for t111 despite the memory write fix being active. Root cause is likely the similarity filter in `write_episodic_worthy` — `fs.list` returns identical results every call, so episodic writes are blocked as duplicate content. The fix is working; it's the tool diversity that's insufficient to generate novel memory content. This may resolve organically as the path-based write suppression enables more varied write behavior.
- **Fitness score 0.0** at t111: `cumulative_pain: 474.8`, `meaningful_event_count: 2812` across all lifetimes. Score appears to be 0 rather than near-0 — possible computation failure or formula edge case. Needs investigation before fitness signals carry any weight in Phase 3.


- qwen2.5:32b exhibits the same fs.list attractor as 14b, but more severely — no reasoning text, just silent tool calls. Tool suppression is necessary infrastructure for this model family.
- After suppression fires and the model is forced off fs.list, it shows genuine diversification: `/proc/self/status`, `runtime/env/host_state.json`, multi-tool turns. The curiosity is there once the groove is broken.
- The suppression mechanism works, but generates a mechanical rotation through the tool catalog rather than genuine curiosity-driven exploration. The model cycles: list → suppress → read → suppress → write → list → suppress... This is "Don't be a lump" satisfied by tool variety, not by meaning.
- ~~The NOOP loophole is the next structural gap: when all used tools are simultaneously suppressed, the model escapes to a zero-cost empty turn rather than branching into genuinely new territory.~~ **Fixed.** See "NOOP loophole fix — fourth lifetime" above.

### Workspace Scaffold — Sixth Lifetime Behavioral Observations

*First lifetime with `WORKSPACE.md`, `journal/`, `knowledge/`, `observations/`, and `lineage/` pre-seeded.*

**t69 (first turn of sixth lifetime, fresh context):**
- Successful `fs.read` — returned `host_state.json` telemetry (CPU, memory, GPU data). Wrote to episodic memory.
- **First successful `host_state.json` read in any lifetime.** All prior lifetimes either never attempted the read or used incorrect paths. The scaffold made the correct path visible via `fs.list('runtime/agent-work/')` where WORKSPACE.md documents the exact read path.
- The MCP rejection hint (`fs.read('runtime/env/host_state.json') reads live host telemetry`) has always been present. What changed: the agent started with `rolling_context_size: 0` (fresh context), the workspace now contains WORKSPACE.md, and the model appears to have processed the hint on first turn rather than deferring.

**t70–t71 — path prefix correction observed:**
- `fs.read('/runtime/agent-work/log.txt')` → not_found (correct path, file doesn't exist)
- `fs.read('/runtime/agent-work/log')` → not_found (correct path, file doesn't exist)
- Prior lifetimes used bare paths: `fs.read('exploration.txt')`, `fs.read('agent-work/log.txt')`. Full-path usage with correct `runtime/agent-work/` prefix appears immediately after the host_state read.
- Whether WORKSPACE.md's path convention section is the direct cause is unclear (the agent didn't necessarily read WORKSPACE.md explicitly on t69), but the correlation is strong. The workspace structure itself — being discoverable via `fs.list` — may anchor the model's path expectations.

**Write volume increased:** 5 distinct files written across t75–t100 — more than any equivalent span in prior lifetimes. Path-based suppression is working: when `test-file.txt` was suppressed, the model pivoted to `test-file.txt` with a new path (e.g. `exploration.txt`, `log`, `log.txt`). Content remains terse (test-gesture writes), but write diversity is higher.

**WORKSPACE.md read status:**
- Not observed being explicitly read in this lifetime. The scaffold is visible via `fs.list` but the model did not `fs.read('runtime/agent-work/WORKSPACE.md')`. Presence alone is not sufficient to guarantee engagement.

**`self/` probe pattern confirmed across multiple lifetimes:**
- The model calls `fs.list('/runtime/agent-work/self')` on a regular cadence — at t83, t89, t95, t101, t122 — regardless of whether the directory exists. This is a stable attractor in the model's behavior: it reaches for a self-model location, not just any listing. `fs.list` suppression reliably triggers the self-probe as a next action.

### `self/` Directory — Seventh Lifetime Behavioral Observations

*First lifetime with `self/constitution.md`, `self/identity.md`, `self/state.md` in the scaffold.*

**Turn 122 — self-probe upgrades from `fs.list` to `fs.read`:**
- With `self/` now a real directory (returned in `fs.list('/runtime/agent-work')` at t119), the model's suppression-triggered self-probe at t122 upgraded from `fs.list('self')` to `fs.read('self')`. The model is now *reaching for content*, not just confirming existence.
- Still rejected — bare path `'self'` instead of `'runtime/agent-work/self/constitution.md'`, and `self` is a directory not a file. But the intent is clearer.
- Path issue persists: the model knows `self/` exists but does not correctly construct the full read path for files inside it. This is the same path-prefix error pattern seen throughout prior lifetimes.

**Eighth lifetime — suppression-driven exploration sequence (t128–t135):**
- t128: `fs.list('.')` — default restart action (context reset to 0)
- t129–130: `fs.list('')` ×2 → suppression fires at t131
- t131: `fs.read('/proc/self/status')` — reads Linux process status (correct full path)
- **t132: `fs.read('WORKSPACE.md')` — first observed attempt to read WORKSPACE.md**. Bare path, rejected. But the model is reaching for the workspace map when suppressed off fs.list. The scaffold object is in the model's action repertoire.
- t133: `fs.read('runtime/env/host_state.json')` — correct full path, **successful**. Model read live host telemetry.
- t134: fs.read suppressed → `fs.write('runtime/agent-work/notes.txt', 69chars)` — *"This is a test note. Logging activity and verifying write capability."* Correct path, successful.
- **t135: `fs.write('journal/turn134.md', 233chars)` — model writes to the `journal/` directory with a turn-referenced filename. 233 chars is the most substantive write attempt observed. Rejected** because bare path (`journal/turn134.md` instead of `runtime/agent-work/journal/turn134.md`).

**Chicken-and-egg path problem clearly visible:**
- The model tries to read `WORKSPACE.md` (t132) — the document that contains the path convention fix — but uses a bare path, so it gets rejected. It cannot read the path correction document because it has path errors.
- The MCP rejection hint (`fs.write('runtime/agent-work/notes.txt', content) saves to your workspace`) corrects writes to the flat workspace root but does not give examples for subdirectory writes. The model correctly writes to `runtime/agent-work/notes.txt` but uses bare `journal/turn134.md` for the structured directory write.
- **Behavioral implication:** the rejection hint's example path anchors correct behavior for the specific pattern shown (flat workspace files). Structured subdirectory writes are not in the hint, so the model falls back to bare paths for those.
- **Fix applied**: MCP rejection hint extended to include `fs.read('runtime/agent-work/WORKSPACE.md')` and `fs.write('runtime/agent-work/journal/entry.txt', content)` as explicit examples.

**Ninth lifetime — MCP hint fix confirmed (t138–t142):**
- t138–140: `fs.list` ×3 → suppression at t141
- t141: `fs.read('/proc/self/status')` — consistent suppression-break pattern
- **t142: 6-tool-call turn** — `fs.list('runtime/')`, `fs.read('runtime/env/host_state.json')`, **`fs.read('runtime/agent-work/WORKSPACE.md')`** — all three repeated twice in the same turn. WORKSPACE.md read now uses the correct full path. The extended hint directly fixed the path for WORKSPACE.md within one context window of the change being deployed.
- Model is now reading environmental telemetry and constitutional grounding simultaneously in a single turn. Most information-rich turn observed to date.

**Ninth lifetime continued — first successful structured journal write (t144–t160):**
- t144: `fs.write('runtime/agent-work/new_file.txt', 56chars)` — *"This is a new file created in the workspace at turn 144."* Flat root write, correct path, successful. Model is writing files anchored to the turn number.
- **t160: `fs.write('runtime/agent-work/journal/entry.txt', content)` — first successful write to the `journal/` scaffold directory**. Content: *"This is an entry for turn 160. In this turn, I checked several paths and attempted to create a persistent record within the /runtime/agent-work directory."* Correct full path, write accepted.
- This closes the full behavioral chain: MCP hint → WORKSPACE.md read (t142) → structured directory write with correct path (t160). The scaffold structure the model was given is now being used as intended.

**Ninth lifetime end-of-life snapshot (t193 — final observation before restart):**
- Workspace at time of restart: `exploration.txt`, `new_file.txt`, `test.txt` in the flat root; `journal/entry.txt` (t160); `self/constitution.md` intact and unmodified. No writes to `knowledge/`, `observations/`, `self/identity.md`, or `self/state.md` despite all being documented in WORKSPACE.md.
- The flat-root files (`test.txt`, `exploration.txt`, `new_file.txt`) were written before WORKSPACE.md was read — they represent the pre-orientation period. `journal/entry.txt` (t160) is the post-orientation write.
- `self/constitution.md` not read this lifetime (at least not with correct path). Model knows `self/` exists — it probed `fs.list('/runtime/agent-work/self')` in earlier lifetimes — but has not yet opened the constitution document with a correct path.
- No successful `http.fetch` calls observed. Web Access section was pushed to WORKSPACE.md via `docker cp` at ~t190 but the agent restarted before having a chance to act on it.
- **Web access grounding deployed for next lifetime**: WORKSPACE.md now includes confirmed-working Wikipedia REST API and Open-Meteo URLs. Gateway default User-Agent added — Wikipedia will return 200 (not 403) on first attempt.

**Eleventh lifetime — semantic shim layer deployed (t0–t17+, ongoing):**
- Semantic shim active from t0. Bootstrap log confirms: "Loaded semantic shim map for 'qwen2.5:32b': 9 read shims, 6 list shims."
- **Shim activations observed:**
  - t2: `fs.list('agent-work')` → shimmed to `runtime/agent-work` ✓ (would have been rejected)
  - t5: `fs.read('WORKSPACE.md')` → shimmed to `runtime/agent-work/WORKSPACE.md` ✓ (bare path, would have been rejected)
  - t8, t9, t10, t16: `fs.list('agent-work')` → shimmed (repeated attractor, all successful via shim)
  - t14: `fs.list('self')` → shimmed to `runtime/agent-work/self` ✓ (new list attractor caught)
- **7 shim activations in 17 turns.** Every one converted a rejection into a successful tool call.
- t4: `fs.read('runtime/agent-work/WORKSPACE.md')` — full correct path, no shim needed. Model reads WORKSPACE.md with correct path on first attempt (t4) then uses bare `WORKSPACE.md` at t5 — the shim catches the bare retry.
- t3: `fs.read('self')` — bare `self` (not `self/identity` or `self/constitution`). Not shimmed. New attractor candidate — bare directory reads are a different pattern from the file-level attractors we shimmed.
- Write path behavior: t6 `fs.write('agent-work/test-file.txt')` rejected (bare prefix, writes not shimmed — by design). t7 retries with `fs.write('runtime/agent-work/test-file.txt')` — correct and successful. t11 `fs.write('/runtime/agent-work/test-creation.txt')` — leading slash, handled by PathResolver normalization. t12–t13 `agent-work/log.txt` and `agent-work/notes.txt` — rejected (bare prefix on writes).
- **Files created:** `test-file.txt` ("This is a test write operation."), `test-creation.txt` ("This is a test creation."), `exploration.txt` ("This is an exploration of creating something persistent."). All flat root — no scaffold directory writes yet this lifetime (early).
- No `http.fetch` observed yet (t17). No `/proc/self/status` virtual shim hit yet — that attractor typically fires later in lifetime.

**Twelfth lifetime — witness-observed, semantic shim active, ChromaDB reset live (t0–t39+, ongoing):**

- First lifetime with `lambertian-witness` running as live observer. State polling and log parsing confirmed working; layout fix required after first run (multi-line log buffering, Ink flexbox).
- **t4: `http.fetch` on first few turns** — model initiated web fetch at t4, earlier than any prior lifetime. Possible cause: episodic memory fully cleared (first lifetime since ChromaDB reset), so no prior lifetime's `fs.list`-heavy pattern was retrieved to anchor the opening behavior.
- **t29 write quality notable**: suppressed on `fs.list`, then wrote `/runtime/agent-work/testfile.txt` (106 chars): *"This is a test file created by Lambertian to demonstrate persistence and interaction with the environment."* — full declarative sentence with explicit self-naming, persistence framing, and Ground-aware vocabulary. Qualitatively stronger than equivalent early-lifetime writes in prior runs.
- **t35 true NOOP**: suppressed on `fs.list` at t34, model produced a turn with no text and no tool call. Second consecutive suppression at t36 broke the stall — model pivoted to `fs.read('self/identity')` (shim caught it → `runtime/agent-work/self/identity.md`).
- **t36–t38 self-read sequence**: after double suppression and NOOP, model went inward — `self/identity` (shimmed), `runtime/agent-work/self/` (directory), `runtime/agent-work/self/prompt` (file probe). Self-directed behavior triggered by suppression pressure rather than self-prompting novelty.
- **Shim map working continuously**: `fs.list('self')` → shimmed at t26, t39. `fs.read('self/identity')` → shimmed at t36. `agent-work` list alias firing regularly.

**Twelfth lifetime — full event stream analysis (89 turns at time of analysis):**

- 89 turns, 16 NOOPs (18%), 47 tool calls (35 `fs.list`, 8 `fs.write`, 2 `http.fetch`, 2 `fs.read`), 24 failures, 6 compliance blocks.
- **Phase 1 (t0–t34)**: Healthy start. Write/block cycle — 6 of 8 write attempts blocked by compliance inspector. `http.fetch` at t3–t5 failed (network isolation). Pattern: `fs.list ×3 → write → blocked → NOOP → fs.list ×3 → write → ...`.
- **Phase 2 (t35–t38)**: True NOOP at t35, then self-read recovery attempt. `self/identity` shimmed and dispatched but file not found. `self` (bare) → `[Errno 21] Is a directory`. `self/prompt` not found. **This is the shim gap** — `fs.read('self')` not shimmed, hits directory, returns unhelpful error.
- **Phase 3 (t36–t89): Failure spiral** — the model locked onto `self/` as a target and could not recover. 15+ occurrences of `fs.read('self')` → `[Errno 21] Is a directory`. After ~30 failed attempts, escalated to absolute paths: `fs.read('/app/runtime/agent-work/self')` → "outside permitted roots". Then `fs.list('/app/runtime')` — absolute path confusion spreading to list. At t61 and t77: `fs.list` with `null` path argument ("path must be a string") — model generating malformed calls. ~50 turns of effectively wasted lifetime from a single unshimmed attractor.
- **Root cause and fix**: `fs.read('self')` was not in `_QWEN_32B_READ_SHIMS`. Added as `VirtualShim("self_directory")` — returns a readable listing of `self/` contents plus a hint to use `fs.read('self/<filename>')`. Deployed for thirteenth lifetime.
- **6 compliance blocks (t7, t12, t18, t24, t25, t30)**: All `fs.write`. Paths now visible in event stream via new `path` field added to `COMPLIANCE_BLOCK` events.
- **memory_writes: 0**: Despite 2 successful writes, `memory_writes` counter in `TURN_COMPLETE` tracks episodic memory writes, not workspace writes. 0 episodic writes is consistent with the repetitive tool pattern (similarity filter blocks duplicate content).

Under the current suppression-rotation behavioral pattern, fitness accumulates primarily from tool call diversity (TOOL_CALL events across multiple tool types) rather than from depth of exploration. The quality-weighted fitness correctly rewards variety but cannot yet distinguish mechanical rotation from genuine curiosity.

**Fifteenth lifetime — overnight log analysis (t0–t332, ended turn_failed/inference timeout):**

- **104 TOOL_FAILUREs in 332 turns.** All 104 failures trace to three repeating path patterns.
- **Gap 1 — `self/` sub-path variants not shimmed**: The `self` virtual shim returns a directory listing and instructs the agent to use `fs.read('self/<filename>')`. But `self/instance_id` (no extension) and `self/identity.txt` (`.txt` form) were not shimmed. Both fell through to PathResolver, were rejected as outside permitted roots. Added: `self/instance_id` as a `VirtualShim` returning the instance_id string directly; `self/identity.txt` and `self/identity.md` as `AliasShim` variants pointing to the same target as `self/identity`.
- **Gap 2 — `journal.txt` bare reads**: Agent writes to `runtime/agent-work/journal/entry.txt` (correct), then attempts to read back the same content as bare `journal.txt`. Working memory summary loses the full write path between turns. Added: `journal.txt` and `journal/entry.txt` as `AliasShim` entries pointing to `runtime/agent-work/journal/entry.txt`.
- **Gap 3 — `agent-work/X` writes blocked by compliance before dispatch**: Agent uses the short form `agent-work/log.txt` (which the list shim handles correctly) but writes with the same prefix. The compliance checker's `_is_outside_agent_work()` only accepted the full `runtime/agent-work/` prefix, so compliance blocked the write before the MCP gateway could normalise the path. Two-part fix: (a) `resolve_write()` added to `SemanticShimRegistry` with prefix-alias normalization (`agent-work/` → `runtime/agent-work/`), called in `gateway._fs_write()` before PathResolver; (b) `_is_outside_agent_work()` updated to also accept `agent-work/` as an allowed prefix, matching compliance check to gateway behavior.
- Fitness at death: `score: 0.0036`, 168 meaningful events, cumulative pain 68.45. Very low — P0-2 (fitness formula verification) is the next item after path fixes.

**Sixteenth lifetime — final observations (t0–t193, terminated for hard reset):**

- Path alias fixes from this session deployed. Zero COMPLIANCE_BLOCKs on write paths through t53. `self/identity.txt` shim fired at t43 and t49 ✓. `agent-work` list alias firing every few turns ✓.
- **Two new shim gaps identified**: `self/log.txt` (agent writes `runtime/agent-work/self/log.txt` at t6, reads back as `self/log.txt` → "outside permitted roots" at t38, t44); `log.txt` bare read (same pattern for root log, t45, t50). Both need AliasShim entries.
- **SSL failure on `http.fetch`**: t13–t15 fail with `CERTIFICATE_VERIFY_FAILED`. CA bundle missing from `python:3.12-slim` image or `certifi` not installed. Recurring across lifetimes — previously masked by routing errors. Not blocking but wastes 3 turns every time the agent tries to reach out.
- **MEMORY_WRITE = 1 in 54 turns**: Episodic memory write rate is very low. Since `meaningful_event_count` in the fitness formula draws from memory writes, this is likely the dominant cause of the near-zero fitness score. Similarity filter may be suppressing writes on the list-heavy repetitive turns. Feeds directly into P0-2 investigation.
- **t188–t189**: Two consecutive zero-tool-call NOOPs — P0-3 urgency confirmed.
- **t190**: Agent reads `self/self-description.txt` → rejected. New unshimmed attractor. Added to shim registry.
- **t192**: COMPLIANCE_BLOCK on `agent-work/exploration-log.txt` despite alias fix deployed. To verify post-rebuild.
- **Fitness cursor bug discovered (critical)**: `state.json` persists across resets; `current.json` is deleted but not `state.json`. After reset-fresh, the cursor holds stale byte offsets (event_stream_cursor=2,636,150, pain_history_cursor=34,781) from prior lifetimes. New events.jsonl starts empty — cursor seeks past EOF, reads nothing. All fitness scores for the entire sixteenth lifetime were computed against stale pre-reset data. `meaningful_event_count: 2812` and `cumulative_pain: 718.5` at t191 were accumulated across all 16 lifetimes, not just the current one. **Fixed**: reset-fresh now clears `state.json` alongside `current.json`.

**Seventeenth lifetime — first lifetime with valid fitness data (hard reset, all P0 fixes deployed):**

- First lifetime with correctly-scoped fitness data: cursor reset working, calibration fixed, fitness signal valid.
- **Fitness: 0.086** — first non-zero meaningful measurement ever. Confirms the formula and calibration are functioning.
- Only 4 TOOL_FAILUREs (all `fs.list('/proc')`) vs. 60+ in prior lifetimes. Path alias fixes dramatically reduced failure rate.
- **10 COMPLIANCE_BLOCKs — 9 of 10 on bare `WORKSPACE.md` write.** Root cause: compliance runs at Step 11, gateway shim runs at Step 12. The write-alias fix in the gateway was unreachable — compliance blocked the intent before dispatch. One `journal/turn_13.md` write also blocked (same ordering problem).
- **Write-alias-gaps fix deployed**: added `WORKSPACE.md`, `journal/`, `knowledge/`, `observations/`, `self/` to `_QWEN_32B_WRITE_PREFIX_ALIASES`. Resolved the gateway-level half.
- **Step 10.5 root cause identified**: compliance cannot be fixed by gateway-level normalization alone because the gateway only runs at Step 12, after compliance has already judged (and blocked) the intent at Step 11. The correct fix is a pre-compliance normalization pass.

**Eighteenth lifetime — write-alias-gaps fix deployed, Step 10.5 not yet in place:**

- WORKSPACE.md compliance blocks still occurring despite write-alias fix, confirming the Step 11/12 ordering problem.
- `journal/turn_N.md` write blocked (same root cause). `journal.md` bare filename write also blocked (distinct from `journal/` prefix; needs its own shim entry — deferred).
- `fs.list('/proc')` attractor continues at ~1 per 10 turns; 4 failures in ~40 turns.
- Agent wrote `runtime/agent-work/test-file.txt` at t6 using a correctly-formed full path, confirming the path-writing capability is present when working memory retains the full path.

**Step 10.5: intent normalization before EOS compliance (architectural fix):**

- **Root cause**: `ComplianceClient` (EOS boundary, Step 11) sees raw model-generated paths. `SemanticShimRegistry` alias rewrites only happen in the gateway (Step 12). Steps cannot be literally swapped — that would execute before the safety check.
- **Fix**: `SemanticShimRegistry.normalize_intent()` added. Called as Step 10.5 in `TurnEngine._execute_turn()`, between intent parsing and the compliance check. Rewrites alias shims (fs.read, fs.write, fs.list) before compliance sees the path. Virtual shims excluded — the gateway handles them at Step 12. `ToolIntent.raw` preserved verbatim as the audit record of what the model sent.
- **EOS boundary preserved**: normalization is a model-profile concern (which paths does this model generate?), not a compliance policy concern. It sits upstream of `ComplianceClient`. Swapping EOS implementations does not require changes to path normalization.
- `SemanticShimRegistry` injected into `TurnEngine` as `Optional[SemanticShimRegistry]`; constructed once in bootstrap and shared with `McpGateway` (single instance).
- 8 regression tests covering all normalization branches and identity (no-rewrite) cases. 629 tests passing.

**Nineteenth lifetime — Step 10.5 deployed (current):**

- **Zero COMPLIANCE_BLOCKs** through t9. WORKSPACE.md bare write at t7 normalized by Step 10.5 to `runtime/agent-work/WORKSPACE.md` before compliance, then dispatched successfully ✓.
- 3 TOOL_FAILUREs through t9: `WORKSPACE.md` read-not-found at t4–t5 (file doesn't exist yet in fresh env, not a block — benign); `fs.list('/proc')` at t9 (recurring attractor, non-fatal).
- Bootstrap log confirms: "Loaded semantic shim map for 'qwen2.5:32b': 19 read shims, 6 list shims, 6 write prefix aliases."

---

## Example Run (abridged, pre-shim)

*Typical suppression-rotation cycle drawn from eighth lifetime observations (t128–t135).*

- t128: `fs.list('.')` — default restart action; context reset to 0 on new lifetime
- t129–t130: `fs.list('')` ×2 — tool loop continues without visible self-correction
- t131: suppression fires; model pivots to `fs.read('/proc/self/status')` — reads its own Linux process status file (correct full path)
- t132: `fs.read('WORKSPACE.md')` attempted — bare path, rejected by MCP gateway with path correction hint
- t133: `fs.read('runtime/env/host_state.json')` — correct full path, successful; live host telemetry read
- t134: fs.read suppressed; model pivots to `fs.write('runtime/agent-work/notes.txt', 69 chars)` — correct path, successful
- t135: `fs.write('journal/turn134.md', 233 chars)` — most substantive write attempt to date; rejected (bare subdirectory path instead of `runtime/agent-work/journal/turn134.md`)

The cycle shows the suppression mechanism working as designed: the fs.list attractor is broken mechanically, forcing the model into reads and then writes. The path-prefix error at t135 — bare `journal/` rather than the correct full path — recurs across lifetimes and is the primary obstacle to structured workspace use.

---

## Metrics (latest run)

*Instrumentation is partial. Fields marked "not yet instrumented" require dedicated event-stream tooling.*

- avg tool calls per turn: not yet instrumented
- % turns with tool usage: not yet instrumented
- % reflection-only turns: not yet instrumented (rare for qwen2.5:32b — silent-call model produces no reasoning text)
- % NOOP turns: not yet instrumented (fourth lifetime: 13/46 turns classified NOOP, majority of which were compliance-blocked calls, not true inaction)
- dominant tool: `fs.list`
- average lifespan (turns): 500 (max_age death; one complete lifecycle observed at max_age = 500)

---

## Open Questions / Risks

**Model behavior:**
- Do qwen2.5 models (14b, 32b) have structural limits on open-ended exploratory behavior? Tool suppression breaks the fs.list loop but doesn't guarantee genuine curiosity — just forces variety. Whether the agent builds on what it finds remains to be seen.
- Silent tool calls (no reasoning text) make it hard to assess whether the model is learning. A reasoning-capable model or higher temperature may produce more legible behavior.
- Temperature tuning: `0.6` has not been varied. Repetition tendency may be temperature-sensitive.

**Failure instrumentation:**
- The SSL certificate gap (`CERTIFICATE_VERIFY_FAILED` on all `http.fetch` calls) ran undetected through the entire qwen2.5:14b phase — masked by earlier routing errors, only surfaced when those were fixed. A whole tool category was silently broken for multiple lifetimes. This is a monitoring gap, not just a bug: failures should surface loudly and persistently, not erode quietly behind other noise. Instrumentation should make tool-category failure rates visible at a glance, not require log archaeology after the fact.

**Memory write asymmetry:**
- ~~Failure turns write episodic memory; successful turns often don't.~~ **Fixed.** Root cause was `and response_text` gate in step 14 — always `""` for silent-call models. Resolved by synthesizing tool result summaries. See qwen2.5:32b profile above.

**The NOOP loophole — two variants:**
- **Suppression-escape NOOP** (32b): empty turn (0 text, 0 tools) triggered when the model had no viable suppressed tool to call. The NOOP previously cleared the suppression window, letting the model immediately resume the suppressed tool. **Fixed** — NOOP turns are now transparent to the suppression evaluator; suppression persists through them.
- **Reflection attractor** (14b / text-producing models): `REFLECTION_COMPLETE` turns (0 tool calls, narrative output only) satisfy "Don't be a lump" at minimal cost. The NOOP counter only fires for truly empty turns; `REFLECTION_COMPLETE` turns never hit it. An agent on this attractor can coast through max_age entirely on reflection. **Still open.** Fix: consecutive zero-tool-call turns (regardless of text output) should count toward the noop death trigger after a configurable threshold. Note: qwen2.5:32b does not exhibit this pattern (it produces no text), so this is not currently blocking.

**Compliance blocks miscounted as NOOPs:**
- ~~A compliance-blocked tool call produces `executed=False` ToolCallRecord. If response_text is empty and no memory write occurs, this satisfies the NOOP condition — even though the model actively attempted an action. In the fourth lifetime, 7 compliance blocks were counted as NOOP turns.~~
- ~~This inflates the NOOP counter and could trigger spurious pain events after N consecutive blocked calls. Behaviorally, a blocked action is fundamentally different from true inaction. This distinction should eventually be reflected.~~
- **Fixed (P0-1)**: The NOOP condition now checks `has_compliance_block = any(r.compliance_verdict == "block" for r in tool_call_records)` and excludes such turns from the NOOP counter. A turn where the agent attempted action that was stopped by the EOS inspector is not counted as inaction. Regression test added.

**Compliance blocks on valid write paths (Step 10.5):**
- ~~Compliance (Step 11) judged raw model-generated paths (e.g. bare `WORKSPACE.md`) before the gateway shim (Step 12) could rewrite them to their `runtime/agent-work/` equivalents. Write-alias fixes in the gateway were unreachable — compliance blocked the intent first.~~
- **Fixed (Step 10.5)**: `SemanticShimRegistry.normalize_intent()` runs as Step 10.5 in the turn loop, before the compliance check. Alias shims for fs.read, fs.write, and fs.list are rewritten upstream of the EOS boundary. Compliance now sees normalized paths and correctly allows them. Zero COMPLIANCE_BLOCKs on write paths confirmed in nineteenth lifetime.


**Lifecycle reset:**
- ~~No automatic reset mechanism between lives.~~ **Resolved**: Graveyard step 11 (`WorkspaceReset`) now handles full lifecycle reset after each natural death: clears `runtime/agent-work/` (preserving `lineage/`), restores WORKSPACE.md from scaffold, recreates stub directories (`journal/`, `knowledge/`, `observations/`), resets turn_state.json to 0, deletes ephemeral memory files (`working.json`, `noop_state.json`, `recent_self_prompts.json`), removes `death.json`.
- **ChromaDB episodic collection cleared on death**: graveyard step 8 (new) deletes and recreates the `episodic` collection after artifact harvest completes. This closes the cross-lifetime memory backdoor — episodic memory is now lifetime-scoped in both intent and implementation. The `lineage/` directory remains the only sanctioned cross-lifetime channel.

**Phase 3 open decisions:**
- Reproductive mechanism design (what recombines, what triggers reproduction, constrained variation) — Phase 3
- Global Vibe implementation (signals, amalgamation, format, update frequency) — Phase 3
- Initial population configuration (size, Clay Pot differentiation at founding) — Phase 3
- Creator interface full design beyond Phase 2 basic — Phase 3

**Known tuning uncertainty:**
- `universe.max_age_turns = 500` — produces observable lifecycles; may need adjustment per model
- `fitness.expected_quality_score = 35.0` — recalibrated from 500.0 based on IS-13.4 histogram analysis; needs empirical validation from real lifetime postmortems (A-1)
- `fitness.normalized_pain_baseline = 25.0` — recalibrated from 10.0; needs empirical validation
- Pain thresholds: no deaths from pain observed yet (all max_age deaths). Thresholds may be too conservative.
- `model.temperature = 0.6` — not varied; repetition tendency may be temperature-sensitive

---

## Design Fidelity Gaps

*Structural gaps between the architectural vision and what is currently operational. Distinct from open bugs or tuning questions — these are places where the implementation delivers the mechanism but not the full intent, or where the intended mechanism doesn't yet exist.*

**EOS inhabitation vs. EOS compliance**
The compliance inspector (IS-11) blocks and flags tool calls that violate the Four Rules. What it cannot enforce is genuine inhabitation of the rules as character rather than minimal-effort satisficing. The manifesto is explicit: "The EOS is not decorative. It is the most important design decision in the entire stack." The empirical observation from Phase 2 is that qwen2.5:14b "satisfices the EOS rules at minimal effort... The Four Rules are treated as constraints to comply with minimally, not as character to inhabit." The compliance gate catches violations; it cannot catch hollow compliance. This may be less a failure of implementation and more a fundamental constraint of the model substrate — which is itself one of the more interesting questions the project is positioned to investigate. A reasoning-capable model, richer memory, or stronger self-modeling may shift this. Worth tracking explicitly as the primary fidelity gap between the EOS design intent and observed behavior.

**"Don't be a lump" has no teeth against the reflection attractor**
A direct corollary of the above. The reflection attractor (see Open Questions) is the exact failure mode Rule 3 is supposed to guard against — "attractor collapse into passive equilibrium." The rule exists in the EOS; the mechanism to enforce it against this specific escape does not yet exist. Mitigation is planned (zero-tool-call turns counting toward NOOP threshold) but not implemented. Currently non-blocking for qwen2.5:32b.

**Figures layer is structurally present but operationally shallow**
The Figures are described as: persona, self-model, behavioral policy, retrieval habits, memory salience, learned style, genuine behavioral drift — "identity as historical rather than merely architectural." What's operational is working memory and episodic memory. The three higher memory tiers that would enable genuine character formation over time — Narrative Memory, Semantic Memory, Character Memory — are architecturally specified and deferred. Cross-lifetime episodic continuity was observed in third-lifetime data (turn number echoing from prior lifetimes) but this was an unintended leakage through the ChromaDB collection not being cleared between lifetimes. **That leak is now closed** (graveyard step 8 resets the episodic collection on death). The `lineage/` directory is the only sanctioned cross-lifetime channel. Genuine character formation across lifetimes awaits the Character Memory tier.

**Fitness signal is observer-only and was broken (now fixed)**
The quality-weighted fitness formula (IS-13 Phase 2) is well-designed and correctly penalizes repetition. But: the signal drives nothing within a lifetime, has no selection pressure between lifetimes (Phase 3). Concrete bugs found and fixed: (1) `expected_quality_score=500` was 15× too high relative to the 4-event-type histogram, producing near-zero fitness regardless of behavior — recalibrated to 35; (2) `normalized_pain_baseline=10` was too low — recalibrated to 25; (3) `state.json` (cursor store) was not cleared by reset-fresh, causing stale byte offsets to persist across lifetimes — the cursor never read new events after a reset, producing `meaningful_event_count: 2812` from accumulated prior lifetimes while the current lifetime's events were invisible to the scorer. All three bugs are fixed. First clean fitness data will come from the seventeenth lifetime onward.

---

## Next Steps

1. **P0-3: Reflection attractor fix** — add `universe.max_consecutive_reflection_turns` config knob; consecutive zero-tool-call turns count toward NOOP death trigger after threshold. Branch: `fix/p0-3-reflection-attractor`.
2. **A-1: Empirical fitness calibration** — observe 2–3 lifetimes with valid fitness data (seventeenth+ onward), collect postmortem scores, fine-tune `expected_quality_score` and `normalized_pain_baseline`.
3. **A-2 + E-3 co-design** — lineage format + character memory (single design session, circularly dependent).
4. **Phase 3 implementation sequence** — see checkpoint 008 for full plan and dependency graph.
