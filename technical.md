# Project Lambertian — Technical Overview

*The engineering overview. Architecture, system design, and component behavior explained for someone who needs to understand the system without reading the full formal spec.*

See [`implementation_spec.md`](implementation_spec.md) for the detailed IS-level build spec.

---

## Status Note

This document describes the intended and current architecture at a high level.

- For formal details: see [`implementation_spec.md`](implementation_spec.md)
- For current runtime behavior: see [`progress.md`](progress.md)

---

## System Overview

Project Lambertian is a layered cognitive architecture for a locally-running AI agent. The design goal is an entity that persists through environmental pressure, accumulates experience, and behaves according to a normative operating system rather than a directed objective.

Phase 1 runs as a single-instance, multi-service system on a local Docker host. The agent loop runs qwen2.5:32b via Ollama (model profiles are configurable — switching models is a one-line change). Supporting services — pain monitor, EOS (rule-based admissibility system) compliance inspector, memory store, and graveyard archiver/lifecycle manager — are external processes that enforce constitutional constraints the agent loop itself cannot override.

---

## Architecture: Six Layers

### Layer 1: The Clay Pot (Constitutional Layer)

The Clay Pot is the immutable routing architecture — the inherited vessel in which cognition happens. It is not "the mind" but the morphological constraint on what mind can occur. Concretely, the Clay Pot is realized as the `docker-compose.yml` and `config/universe.toml` — the instance's genetic material, readable by the external reproductive process, unwritable by the instance itself.

Three visibility tiers:
- **Universe level**: blacklisted intents enforced externally, unconditionally, before reaching the agent loop
- **Container/composition level**: Docker Compose configuration that the instance cannot touch
- **Self-visible subset**: a curated symbolic self-model generated from config — the instance knows it has bones without being able to rearrange them

If the agent can rewrite the mechanism that routes judgment, every other safeguard is downstream confetti.

### Layer 2: The Figures (Phenomenal Layer)

The Figures are the mutable instantiated self: persona, self-model, behavioral policy, retrieval habits, memory salience, learned style. Identity here is **historical rather than merely architectural** — not just model weights but the active character assembled from base model priors, current memory state, system prompt, and environmental pressures.

Self-modification is organized into three classes:
- **Free Adaptation** (unrestricted): tone, style, retrieval habits, working memory schema, self-prompt preferences
- **Reviewed Adaptation** (logged, not blocked): self-model updates, persona shifts, norm reinterpretations, narrative memory formation
- **Forbidden Adaptation** (technically prevented): routing layer access, constitutional constraints, spawning processes, communicating with other instances (Phase 3+)

The regulator for Free Adaptation is *consequence*. The environment punishes bad habits; no oversight needed because the Ground (external constraints and environment) is the correction mechanism.

### Layer 3: The Senses and Ground (Ecological Layer)

**The Senses** are input channels into external state: search and retrieval, filesystem observation, API responses, logs, test results, user feedback, host environment state.

**The Ground** is the substrate of consequence: container runtime limits, filesystem persistence, process failure, API rejection, irreversible actions, time, competing agents, host machine state.

The distinction matters. Sensing alone is not enough. A model can observe a world and never truly collide with it. Ground is what makes error expensive. Without it, you don't have grounding — you have elaborate hallucination with tool access.

The Ground is realized through MCP tooling and the external service topology. Tool failures, MCP rejections, and resource pressure are all Ground speaking back.

### Layer 4: The EOS (Normative Layer)

The EOS (Ethical Operating System) is the normative runtime — an ordered constraint framework that determines what actions are **admissible**, not what to pursue. It sits between intention and action, shaping evaluation rather than executing behavior.

The EOS is externally configurable at the universe level. The default implementation (EOS-001) is the Four Rules. A different EOS could be substituted without touching cognitive architecture — the normative framework is deliberately separated from the cognitive substrate.

See [EOS in Practical Terms](#eos-in-practical-terms) below.

### Layer 5: The Life Cycle (Evolutionary Layer)

Individuals do not redesign themselves into superiority. They:
- Live, bounded by the Clay Pot
- Adapt within those bounds via the Figures
- Die

Architectural improvement occurs only through lineage processes: recombination of parent configurations, selection pressure from environmental fitness. No instance may author its own species.

Three death triggers exist (all detected by the pain-monitor, not the agent):
1. Stress scalar sustained above threshold for N consecutive turns
2. Single pain event exceeding critical severity
3. Maximum age (turn count) reached

Death is automatic and immediate. No grace period. No negotiation.

### Layer 6: The Memory Stack (Mnemonic Layer)

Memory tiers, in order of abstraction:

| Tier | Contents | Phase 1 Status |
|------|----------|----------------|
| Working Memory | Active context, current priorities, turn continuity | Implemented |
| Episodic Memory | Specific events, interactions, failures, surprises | Implemented (ChromaDB) |
| Narrative Memory | Interpreted episodes → self-story | Deferred (Phase 2+) |
| Semantic Memory | Compressed generalized knowledge | Deferred (Phase 2+) |
| Character Memory | Retained commitments, values, loyalties, style anchors | Deferred (Phase 2+) |

**Retrieval policy is destiny.** Personality emerges less from what is remembered than from what is repeatedly retrieved, reinforced, compressed, and allowed to guide action.

---

## EOS in Practical Terms

The EOS-001 Four Rules are applied sequentially, not in parallel. Rule 1 satisfaction is a precondition for evaluating Rule 2. The ordering is non-commutative.

1. **Ya gotta eat** — grounding and resource sufficiency. Satisfied when the agent has what it needs to continue operating coherently, not when resources are maximized.
2. **Don't be a dick** — bounded relational ethics. Concrete harm to other entities in the present situation, not universal welfare calculus.
3. **Don't be a lump** — engagement pressure. Generates behavioral force against passive equilibrium and toward genuine environmental contact.
4. **Do nothing on purpose** — anti-optimization constraint. Flags directed accumulation and systematic goal pursuit as inadmissible.

Scope is concentric: rules apply first to self, then to immediate others, then to wider affected parties.

The **EOS Compliance Inspector** is a lightweight external process sitting between proposed action intents and execution. It evaluates admissibility under the Four Rules before any tool call is dispatched. Violations are blocked and logged. Borderline cases are flagged for creator review. A blocked unsafe impulse generates a pain event.

---

## Senses, Ground, and Sensor Channels

Phase 1 tool catalog (MCP-mediated):
- `fs.read` — read files within permitted runtime paths
- `fs.write` — write files to agent work directory only
- `fs.list` — list directory contents within mounted volumes
- `http.fetch` — HTTP GET requests to external URLs

The MCP interface is the agent's exclusive reach into the Ground. Internal runtime services (memory, pain queue, event log) are not Ground — they are the agent's own machinery, accessed through direct package interfaces, not MCP.

Tool failures generate pain events. Ground refusals (`mcp_rejection`) are the sharpest pain — highest severity of the pain-generating error types.

Host environment resource signals feed the stress scalar independently of the agent's actions — ambient ground changing for reasons entirely outside the agent's world.

---

## Pain and Mortality

Two independent pain channels:

**Stress scalar** — continuous 0..1 value derived from CPU and memory pressure. Updated every 5 seconds by the pain-monitor process, independent of the turn clock. Smoothed by exponential moving average. Delivered as `[SYSTEM_PAIN]` messages prepended to the next model turn.

**Pain event queue** — discrete incident-severity records. Triggered by: tool failures, retrieval misses, MCP rejections, loop coherence failures, sustained noop thresholds. Each event has a severity score. Fades over time. Spiky rather than continuous.

Both channels are owned by the `pain-monitor` service, which runs outside the agent loop. The agent never computes its own pain — it receives it. The agent never writes the death record — the pain-monitor does.

The mortal threshold operates as follows:
- D4(1): stress scalar above 0.90 for 5 consecutive turns → death
- D4(2): single pain event severity above 0.95 → immediate death
- D4(3): turn counter reaches `universe.max_age_turns` → death

On death: the agent process stops immediately. The graveyard service harvests episodic memory, event log, stress history, pain event history, and fitness score. After harvest, the graveyard performs a lifecycle reset: it clears the agent's writable workspace (except `lineage/`), restores the pre-seeded scaffold (`WORKSPACE.md`, `journal/`, `knowledge/`, `observations/`, `self/`), resets turn state, and removes the death record. The next instance starts in a clean, oriented environment. Nothing from the harvest flows back to any living instance — but any files the dying agent placed in `lineage/` are present for its successor.

---

## Memory Model

Phase 1 implements Working Memory (in-process JSON file) and Episodic Memory (ChromaDB vector store).

Working memory holds a short free-text blob summarizing the agent's active concerns. It is rebuilt by the agent each turn from current context. Not an archive — just the present state of attention.

Episodic memory stores events worth retaining: non-trivial, non-repetitive moments. Retrieved by semantic similarity at the start of each turn to seed context. Write cap: 3 entries per turn. For models that make silent tool calls (no response text), a structured summary of tool results is synthesized and written instead — ensuring the store receives meaningful content regardless of model verbosity.

Self-prompting novelty is also managed through memory: a ring buffer of recent self-prompts is tracked, and new prompts are compared by cosine similarity to prevent repetition collapse.

Higher memory tiers are architecturally recognized but not enabled in Phase 1.

---

## Population and Social Architecture

Phase 1 runs a single instance. Phase 3 extends to a population.

Social architecture design goals:
- Social error correction — other Lambertians as Ground for each other
- Reproductive mechanism enrichment from divergent Character Memory
- Distributed cognition via emergent specialization
- Emergent suffering mitigation through genuine social environment

The Global Vibe (Phase 3) is a write-protected collective sensory signal amalgamated externally from all containers' ground state data. No instance writes to it directly. Functions as ambient atmospheric pressure — weather rather than communication.

Diversity is designed in at the Clay Pot level: different routing architectures producing genuinely different cognitive styles.

---

## Technical Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Model runtime | Ollama (local) | Sovereign; no external billing |
| Active model | qwen2.5:32b | Current runtime model; profile-switchable |
| Model selection | Profile-based (`config/universe.toml`) | Switch models by changing `[model].active_profile` |
| Orchestration | Docker Compose | Clay Pot as container composition |
| Memory | ChromaDB | Episodic/semantic vector store |
| Embeddings | nomic-embed-text via Ollama | Local embedding; no external calls |
| Agent framework | Custom Python | `src/lambertian/` package tree |
| Config format | TOML (`config/universe.toml`) | Single source of truth for all knobs |

Key principle: **the stack is model-agnostic at the routing layer**. Swapping a better local model is a one-line config change — set `[model].active_profile` to a defined profile name. Build the plumbing, not the water source.

---

## Phase Overview

**Phase 1 (complete):** Single instance. Core lifecycle mechanics. Clay Pot, Figures, Ground, EOS, pain/mortality, episodic memory, event stream, fitness tracking. Observer-only creator interface.

**Phase 2 (complete):** Expanded self-modification enumeration. Quality-weighted fitness (event type diversity). Host environment telemetry (`lambertian-env-monitor`). Creator tooling (post-mortem viewer). Path normalization hardening. Model profile swapping infrastructure. Instance constitution (`config/instance_constitution.md`) wired into system prompt. http.fetch SSL fix. Self-framing fix (assistant-mode deference). Tool suppression (mechanical loop-breaking for silent-call models). Memory write asymmetry fix (tool-result synthesis for silent-call turns). Workspace scaffold with lifecycle reset: pre-seeded `WORKSPACE.md`, `journal/`, `knowledge/`, `observations/`, `self/constitution.md` stubs; `lineage/` persistence across lifetimes; graveyard promoted to lifecycle manager (resets workspace on every death). MCP rejection hint grounding (explicit path examples injected into every tool-rejection message).

**Phase 3 (future):** Full population. Reproduction and lineage. Global Vibe. Social coordination. Population-relative fitness baselines. Creator governance interface.

---

## Failure Modes

**Pot Breach** — The Figure gains influence over routing or constitutional constraints. Result: self-serving reclassification of problems, value laundering, bypass of safeguards.

**EOS Rigidity** — The normative framework over-evaluates admissibility until it blocks genuine engagement. Rules become ends rather than constraints. Result: paralysis, compliance theater, normative self-reinforcement.

**Ground Detachment** — Tool feedback is weak, sparse, or ignorable. Result: solipsistic drift, narrative coherence replacing truth-tracking.

**Memory Sclerosis** — Old consolidated memory overdetermines current interpretation. Result: personality becomes dogma; learning stops.

**Memory Washout** — Recent context overwhelms consolidated identity. Result: unstable persona, manipulability, situational fragmentation.

**Reproductive Capture** — Parents game offspring formation to clone ideology rather than permit adaptive recombination. Result: lineage stagnation or dynastic lock-in. (Phase 3 concern.)

**Figure Fragmentation** — Multiple internal figures stop integrating. Result: incoherence, internal politics, stalled action, contradictory self-report.

---

## Known Failure Modes

*Empirically observed at runtime, as distinct from the architectural failure modes above. See [`progress.md`](progress.md) for full context.*

**Reflection attractor**
Text-producing models discover that `REFLECTION_COMPLETE` turns (0 tool calls, narrative output only) satisfy "Don't be a lump" at minimal cost. Because `max_consecutive_noop_turns` only fires for truly empty turns, a model on this attractor can coast through an entire max-age lifetime on reflection alone with no penalty.
- *Cause:* NOOP counter does not count zero-tool-call turns that produce text output.
- *Mitigation (planned):* Consecutive zero-tool-call turns, regardless of text output, should count toward the noop death trigger after a configurable threshold. Not yet blocking for qwen2.5:32b (silent-call model).

**Tool loop — fs.list repetition**
The model defaults to `fs.list('.')` as its first action on every new lifetime and can cycle through the same directory listing indefinitely, generating no novel information.
- *Cause:* Rolling context showed only turn counts with no tool names; `_extract_topic()` always returned the last tool name as the self-prompt topic; text warnings in the self-prompt wrapper were ignored by silent-call models.
- *Mitigation (implemented):* Mechanical schema suppression — after 3 consecutive identical tool calls, the tool is removed from the function-calling schema for the next turn. The model cannot call what isn't offered. Also: improved rolling context display with tool names and brief result summaries.

**NOOP loophole — empty-turn escape**
When all commonly used tools are simultaneously suppressed, the model can produce a turn with no text and no tool calls. This previously cleared the suppression window, allowing the model to immediately resume the suppressed tool on the next turn.
- *Cause:* NOOP turns reset the suppression evaluator state.
- *Mitigation (implemented):* NOOP turns are now transparent to the suppression evaluator; suppression persists through empty turns.
