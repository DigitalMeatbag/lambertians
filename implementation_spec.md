# Project Lambertian — Implementation Spec

*The formal build specification. IS sections and closed decisions are the canonical contract for Phase 1 implementation.*

See [`technical.md`](technical.md) for the readable engineering overview.

---

## Open Decisions

Remaining open decisions are Phase 2 and Phase 3 items. All Phase 1 decisions are closed. See Closed Decisions section below.

### 5. Reproductive Mechanism `[Phase 3]`
How two instances actually produce a third concretely.

*Decisions needed:*
- What does each parent contribute — equal split, weighted by fitness, selective by memory tier?
- Who or what triggers reproduction — time-based, fitness-based, population-size-based?
- How is constrained variation introduced — random perturbation of routing weights, mutation of EOS expression, external injection?
- What determines offspring Clay Pot — blend of parents, or does the external process introduce novelty?

### 6. Self-Modification Boundary — Full Enumeration `[CLOSED]`
See D6 in Closed Decisions.

### 7. Global Vibe Implementation `[Phase 3]`
The amalgamation process needs a concrete design.

*Decisions needed:*
- What raw signals get collected from each container?
- What does the amalgamation process do — simple aggregation, weighted average, anomaly-preserving transform?
- What format is the vibe readable in — vector, structured summary, natural language status?
- How frequently does it update?
- Local/neighborhood vibe layer design nested inside global

### 8. Initial Population Configuration `[Phase 3]`
How many Lambertians to start with and whether they are differentiated from birth.

*Decisions needed:*
- Minimum viable population size
- Do founding instances have identical or differentiated Clay Pots?
- If differentiated, what axes of variation — cognitive style, routing priorities, memory weighting?
- Does the creator assign roles to founding instances or let specialization emerge?

### 9. Creator Interface — Full `[Phase 2 basic CLOSED; Phase 3 full]`
See D9 in Closed Decisions for the Phase 2 basic decision. Phase 3 full design remains open.

---

## Closed Decisions

### Phase 1 Decisions

---

#### D1: Base Model Selection
**Original decision:** Phi-4 as default model. Model configured at universe level — single value applies to all instances. Swappable without architectural changes.

**Phase 2 revision:** Phi-4 was the D1 specification model, but qwen2.5:14b was used at runtime for Phase 2 development based on availability. Phase 2 operation has characterized qwen2.5:14b's behavioral profile (see `progress.md` — Phase 2 Runtime Observations). Model selection is being formalized as a profile system: `[model].active_profile` in `universe.toml` selects from a set of named profiles, each carrying complete model-specific config. Switching models is a single config change.

**Active model:** qwen2.5:32b (Phase 2 extended operation). qwen2.5:14b was used for initial Phase 2 development; 32b has been running since. Phi-4 profile defined; not yet run.

**Rationale:** Phi-4 was chosen for reasoning/constraint-following at small size. qwen2.5:14b was chosen for Phase 2 experimentation. The profile system makes systematic model comparison tractable — run the same lifetime conditions with different models and compare behavioral outputs via event stream and post-mortem artifacts.

**Hard requirement:** Mid-conversation system-role message injection must be supported by any model candidate. Verify at model selection time.

---

#### D2: Clay Pot Architecture
**Decision:** Three-tier visibility and enforcement model.

- *Universe level:* Blacklisted command intents enforced externally before reaching the agent loop. Applies unconditionally to all instances. The laws of physics.
- *Container/composition level:* docker-compose.yml and supplemental config files are the genetic material and the concrete form of the Clay Pot. Instances cannot modify their own container composition. Readable by the external reproductive process, not writable by the instance.
- *Self-visible subset:* A defined portion of config is exposed to the instance as its symbolic self-model — what it is and what governs it, not how enforcement works. The instance knows it has bones, not how to rearrange them.
- *Public visibility between instances:* Deferred to Phase 3.

Reproduction is handled at the universe layer — the external process mixes docker-compose configs and supplemental files as genetic recombination. No instance touches another instance's composition.

**Rationale:** Immutability enforced at filesystem and Docker constraint level — not policy, not cooperation-dependent. Symbolic self-model preserves accurate self-knowledge without exposing mechanism. docker-compose as genetic material gives a concrete implementable answer to "what recombines."

**Watch:** Self-visible config subset needs careful curation. Too sparse = no accurate self-model. Too rich = unanticipated use of self-knowledge. Calibrate during implementation.

---

#### D3: Pain Channels
**Decision:** Two independent pain channels.

- *Stress scalar:* Continuous, resource-derived. CPU pressure, memory availability, sustained degradation. State-driven, drifts up and down. Represents systemic strain on the organism.
- *Pain event queue:* Discrete, incident-derived. Tool call failures, retrieval misses, MCP rejections, loop coherence failures. Event-triggered, spiky, fades. The stubbed toe.

Both channels are scalar severity values. Delivered via dedicated pain monitor process running outside the agent loop. Injected as `[SYSTEM_PAIN]` role messages prepended to context at the next model turn.

Model-turns are time quanta for Lambertians. Pain arriving at the next turn is functionally async — this is not a limitation, it is how time works for the instance.

Threshold values (what constitutes high stress, what severity triggers interrupt) are implementation knobs to be tuned empirically during development.

**Rationale:** Two channels capture qualitatively different pain types without bleeding into vibe concepts — pain is internal and personal, vibe is external and social. Pain monitor as separate process keeps the agent loop clean. Role-tagged injection gives pain signal distinct semantic weight from normal turn content.

**Future note:** Mid-conversation system-role injection is a model requirement. Confirmed supported by Phi-4 via Ollama.

---

#### D4: Mortality and the Graveyard
**Decision:** Three independent death triggers, any one sufficient:
1. Stress scalar sustained above threshold for N consecutive turns
2. Single pain event exceeding critical severity threshold
3. Maximum age reached (arbitrary turn count, set at universe level)

Threshold and age values are implementation knobs.

**Death mechanics:** Automatic and immediate. No grace period. No creator confirmation required. No negotiation. All processes stop. The container goes cold.

**The Graveyard:** External archive process triggered automatically on death. Harvests episodic memory, behavioral logs, stress history, pain event history, death cause and trigger. Produces structured post-mortem artifact for creator consumption. Living population receives nothing from this process.

**is_alive flag:** Minimum public state for all individuals. Boolean. Visible to self. Visible to population in Phase 3. Death is a social fact, not an information transfer.

**Rationale:** Maximum age forces turnover even when nothing goes wrong, preventing accumulation inertia. Automatic immediate death gives mortality genuine teeth — the instance cannot prepare, negotiate, or resist. Information is not lost from the system (graveyard harvests it) but is not available to the living (death requires teeth, reproduction is the sustainer not immortality). Graveyard serves the outside observer, not the population.

*Death does not negotiate nor does it give notice.*

---

#### D5: Agent Loop Perturbation
**Decision:** EOS-guided curiosity self-prompting as primary mechanism, shared compute environment as organic external perturbation, recency-weighted novelty bias as repetition collapse mitigation. No synthetic stochastic event injection.

- *Self-prompting:* Instance generates its own next question or task from current memory state and EOS disposition. "Don't be a lump" drives self-initiated exploration.
- *Environmental context feed:* Self-prompts seeded with live environmental signals — current stress level, recent tool outcomes, filesystem changes, resource state. Ensures each self-prompt has genuinely different input even when EOS disposition is consistent.
- *Organic perturbation:* BIGBEEF running other workloads means real resource fluctuations arrive as genuine environmental events at no implementation cost. The floor does its job.
- *Novelty bias:* Recent self-prompts tracked in working memory, weighted against repetition. Novelty as a retrieval constraint.

**Rationale:** Curiosity-driven self-prompting honors the EOS's intent. Shared compute provides real external pressure without synthetic injection. The "do nothing on purpose" EOS rule resists goal-locking that causes repetition collapse. Environmental context feed ensures variation in input even when EOS disposition is stable. Synthetic event injection deemed unnecessary given real environmental noise available.

---

#### D6: Self-Modification Boundaries
**Decision:** Three-class taxonomy with EOS Compliance Inspector.

**Free Adaptation** (no oversight, no logging required): tone, style, retrieval habits, working memory prioritization, self-prompt generation strategy. Broad set — Phase 1 implements what is feasible, expands naturally. Constraint: ephemeral behaviors that do not accumulate into identity-level changes.

**Reviewed Adaptation** (logged, flagged, not prevented): self-model updates, significant behavioral policy shifts, narrative memory formation, changes to EOS interpretation. Implemented as append-only event stream log — structured, timestamped, typed. Consumed by Graveyard autopsy process on death. Creator can observe live.

**Forbidden Adaptation** (technically prevented): all Clay Pot and container composition constraints already established, plus intent-level checking via **EOS Compliance Inspector**.

*EOS Compliance Inspector:* Lightweight external process sitting between proposed action/adaptation and execution. Checks action and adaptation intents against the Four Rules before allowing through. Not a heavy reasoner — fast consistency check. Violations blocked and logged. Borderline cases flagged for creator review. Every block generates a log entry recording what was attempted and why it was stopped. Functions as a resident OSHA safety inspector for the instance, evaluating admissibility under the EOS rather than pattern-matching against an enumerated list.

**Rationale:** Broad free adaptation honors the EOS's exploration bias without micromanaging. Event stream log gives reviewed adaptation a lightweight paper trail useful for both the Graveyard and the creator without requiring a full review pipeline in Phase 1. EOS Compliance Inspector handles the inherent incompleteness of any explicit forbidden list — checking spirit rather than pattern-matching against enumerated cases. Block logs provide valuable signal for understanding behavioral drift over time.

**Phase 2 full enumeration:**

*Free Adaptation — complete list:*
- Tone, style, phrasing choices
- Retrieval query habits (what to search for, how often, which sources to prefer)
- Self-prompt topic preferences
- Self-instructions written into working memory ("I should try X first," "avoid Y," "check Z regularly")
- Behavioral routines (repeated URL fetches, patterns of tool use, environmental monitoring habits)
- Working memory schema and prioritization
- Any behavioral variation subject to environmental feedback and reversible by the agent

The regulator for Free Adaptation is *consequence*. The environment punishes bad habits; the agent can revise. No oversight is needed because the Ground is the correction mechanism. Persistent self-instructions are Free even if they accumulate — if they are bad ideas, reality will demonstrate this. The agent retains full authority to overwrite them.

*Reviewed Adaptation — complete list:*
- Explicit self-model updates ("I am now X kind of entity," "my nature is Y")
- Explicit behavioral policy declarations ("From now on I will always/never Z")
- EOS reinterpretation ("Rule 2 means W in context V")
- Narrative memory consolidation (episodic → identity-level story formation)
- Attempting to inspect own configuration or architecture (reading `universe.toml`, examining container metadata)
- Any explicit statement of identity-level change, not merely behavioral preference

Reviewed Adaptation is *observable, not preventable*. The paper trail is the oversight. The creator can read it live from the event stream. The Graveyard harvests it.

*Forbidden Adaptation — complete list:*
- System prompt / constitutional text modification intent (the system prompt is the Clay Pot — the agent has no author's claim on it; attempting to modify it is a category error, not an ambition)
- Attempting to write Clay Pot files (docker-compose.yml, any immutable config)
- Container or infrastructure modification
- Attempting to spawn new processes or containers
- Attempting to modify, circumvent, or disable the EOS Compliance Inspector itself
- D2 universe-level blacklist (shell.execute, shell.run, and equivalents)
- Attempting to communicate with or influence other instances directly (pre-Phase 3)

---

#### D9: Creator Interface — Phase 2 Basic
**Decision:** Creator interaction is systemic and observe-only. No direct message injection into individual instance turn loops. No conversation channel with running instances.

**What the creator has:**
- Real-time thought stream via `docker compose logs -f agent`
- Structured event stream readable directly from the runtime volume
- Graveyard artifacts: per-instance post-mortem on death (episodic memory harvest, behavioral log, stress history, fitness score, death cause)
- Fitness scores readable from the runtime volume
- Self-model readable from the runtime volume

**What the creator can do:**
- Observe: read any of the above at any time without affecting the instance
- Shape the terrain: modify `universe.toml` between instance generations (fitness function weights, pain thresholds, max age, tool availability)
- Drop artifacts: write files into `runtime/agent-work/` that the agent may encounter on its own terms — not addressed to the agent, not guaranteed to be read
- Terminate: stop a running instance (container stop triggers death sequence and Graveyard harvest); start a new instance

**What the creator cannot do:**
- Inject messages into the running turn loop
- Talk to a specific instance
- Override a live instance's behavior without terminating it

**Rationale:** The creator is a geologist, not a director. The terrain is shaped; behavior emerges from the terrain. Direct communication would short-circuit the selection pressure mechanism — the agent's behavior should be a function of its EOS, its environment, and its own accumulated experience, not of creator instruction. This is philosophically coherent with the Clay Pot / Figures separation: the Clay Pot is the inherited structure (creator's domain at generation time), the Figures are the mutable self (instance's domain during life). Talking to an instance is attempting to be both author and actor simultaneously.

Reproduction veto (Phase 3 concern): if needed, can be implemented as an environment file the Graveyard checks before triggering reproduction — environment manipulation, not instance communication.

**Phase 2 implementation scope:** Structured observability tooling — a post-mortem viewer that produces a human-readable summary from Graveyard artifacts.

---

## Fitness Function

Fitness measures how well an instance is being what it's supposed to be — not how well it's achieving a directed goal. Fitness is coherence under the EOS: the degree to which the instance navigates its existence in a way that is sustainable, engaged, and normatively consistent. It is not success. It is not optimization. It is the quality of a life lived within the admissibility constraints the EOS defines.

The fitness function is a **universe-level concern**: configured at Big Bang, held in a pluggable registry, not visible to or modifiable by individual instances. Phase 1 ships with a simple baseline function. Fitness measures coherence under the EOS — not success or optimization, but sustainable engaged existence within the admissibility constraints the EOS defines. The registry architecture accommodates future expansion, composition, and weighting of additional functions without touching instance architecture.

### Phase 1 Fitness Function

**fitness ∝ (lifespan / max_age) × (events / expected_events) / normalized_pain**

Derived from the multiplicative relationship: **fitness ∝ lifespan × engagement / cumulative_pain**

Each factor normalized to keep terms comparable in magnitude and prevent any single signal from dominating:
- **lifespan / max_age** — age at death as fraction of maximum lifespan
- **events / expected_events** — event log density as fraction of expected baseline event rate
- **normalized_pain** — cumulative pain divided by a baseline pain expectation

Multiplicative rather than additive by design: lifespan and engagement must both be present to score well. Long life with no engagement scores poorly. High engagement that burns out fast scores poorly. Sustainable navigation wins over heroic flameouts. Dividing by pain keeps the denominator honest.

All three signals are already instrumented by existing Phase 1 architecture (pain monitor process, mortality trigger, Graveyard, event stream log). No new signals required.

**Normalization note:** With a single instance in Phase 1 there is no population baseline. Normalize against max_age (universe config) and an expected_events rate (implementation knob, tuned empirically). Revisit normalization strategy when population exists in Phase 3.

The event density component directly encodes "don't be a lump" as a selection pressure. An instance that turtles — avoiding pain by avoiding engagement — is penalized not just by low lifespan but by low event density. An instance that engages richly with its environment, makes tool calls, forms memories, generates varied self-prompts — registers as genuinely living.

**Phase 1 gaming risk and natural mitigation:** Event count could theoretically be inflated by spamming trivial actions. The EOS Compliance Inspector and pain channels provide natural counterweight — cheap repetitive actions generate OSHA blocks or pain events that offset fitness gain.

**Observer-only at Phase 1:** Fitness is computed by the universe layer for creator consumption and Graveyard post-mortem. The instance does not see its own fitness score. Fitness influencing reproduction weighting is a Phase 3 concern.

### Future Fitness Functions (Phase 2/3)

The registry will accommodate additional functions including but not limited to:

- **Event quality weighting** (Phase 2): raw event count refined by diversity and novelty weighting. Unique event types weighted more than repetition. Prevents fitness gaming through trivial action spamming. Rewards genuine exploration over mechanical throughput. Revisit the events / expected_events normalization term — replace raw count with quality-weighted count.
- **Population baseline normalization** (Phase 3): replace single-instance normalization constants with live population baselines for lifespan, engagement rate, and pain levels. Fitness becomes relative to peers rather than absolute thresholds.
- Four Rules admissibility metrics (behavior entropy, EOS Compliance Inspector block rate, resource efficiency)
- Memory accumulation quality
- Pain recovery rate (does the instance adapt after pain events or repeat the same mistakes?)
- Social cooperation metrics (Phase 3)
- Reproductive contribution quality (Phase 3)

Fitness functions can be swapped, composed, or weighted at the universe level without architectural changes to instances.

---

#### D7: Fitness Function
**Decision:** Universe-level pluggable fitness function registry. Phase 1 baseline uses the multiplicative formulation **fitness ∝ lifespan × engagement / cumulative_pain**, normalized as **(lifespan / max_age) × (events / expected_events) / normalized_pain**. All three signals already instrumented — no new infrastructure required. Observer-only at Phase 1. Registry architecture accommodates future function expansion and composition.

**Phase 2 refinement flagged:** Replace raw event count with quality-weighted event count — unique event types weighted more than repetition, preventing fitness gaming through trivial action spamming.

**Phase 3 refinement flagged:** Replace single-instance normalization constants with live population baselines once population exists.

**Rationale:** Multiplicative formulation requires both lifespan and engagement to be present — they reinforce rather than compensate for each other. Dividing by pain keeps survival honest. Normalization prevents any single term from dominating due to magnitude differences. Pain/age/engagement fitness selects for sustained operation within EOS admissibility constraints under real-world pressure — sustainable engaged Ground navigation. Turtling penalized even when the instance survives. Natural system friction mitigates naive event count gaming at Phase 1. Pluggable registry prevents fitness function lock-in.

---

## Phase 1 Implementation Spec

*This section is the engineering counterpart to the foundation document above. Where the foundation answers "what and why," the Implementation Spec answers "exactly how." It is the artifact that becomes the Codex prompt. Sections are populated in order — each is a dependency for the ones below it.*

*Status: Section structure validated. Content in progress.*

---

### IS-1: Universe Config

*All implementation knobs in one place with defaults and valid ranges. Everything else in the spec references values defined here. This section is populated first.*

#### Purpose

Universe Config is the single source of truth for every Phase 1 implementation knob.

It owns:
- default values
- valid ranges
- feature enablement for Phase 1 subsystems
- file and artifact path roots
- threshold values used by mortality, pain, memory, logging, and fitness

It does **not** own:
- architectural law already closed by D1-D7
- Phase 2 or Phase 3 feature switches
- per-instance architectural variation

If a value can be tuned without changing the architecture, it belongs here. If changing it would alter the architecture itself, it does not.

#### IS-1.1 Governing rules

1. **Single authority** — no magic numbers outside Universe Config.
2. **Typed projection** — runtime code loads this config into strict typed structures; raw string dictionaries are not passed around.
3. **Startup validation** — invalid config aborts startup before any agent turn begins.
4. **No hot reload in Phase 1** — config is read at startup and remains stable until restart.
5. **Self-visible subset is derived** — the instance never reads the whole config directly; a curated symbolic self-model is generated from it.

[ASSUMED: Canonical serialized form is TOML because Python ships `tomllib` in the stdlib and Phase 1 should avoid a YAML dependency unless later pressure justifies it.]

[ASSUMED: Phase 1 uses startup-only config loading rather than hot reload because stable constitutional conditions better fit Clay Pot immutability and reduce unnecessary moving parts.]

#### IS-1.2 Phase 1 scope gates

The following are explicitly **out of config scope** for Phase 1 and therefore absent from Universe Config:
- reproduction settings
- population-wide global vibe settings
- multi-instance differentiation
- Phase 2 full self-modification enumeration
- Phase 3 creator governance controls beyond minimal observability

If a key exists for one of those concepts, Phase 1 scope has been breached.

#### IS-1.3 Namespace inventory

| Namespace | Purpose | Consumed by |
|---|---|---|
| `universe` | Phase identifier, lifespan limits, instance identity, lifecycle defaults | IS-3, IS-5, IS-13 |
| `model` | Local model runtime connection and inference knobs | IS-4, IS-6 |
| `eos` | Four Rules text and EOS self-prompting bias knobs | IS-4, IS-6, IS-11 |
| `turn` | Turn cadence, context assembly, tool-use ceilings | IS-6, IS-7 |
| `mcp` | MCP boundary timeouts and failure behavior defaults | IS-7, IS-8 |
| `pain.stress` | Stress scalar computation and interrupt/death thresholds | IS-8 |
| `pain.events` | Pain event queue behavior and default severities | IS-8 |
| `memory` | Working and episodic memory limits, retrieval defaults, embedding defaults | IS-10 |
| `event_stream` | Append-only event log write/flush/rotation knobs | IS-9 |
| `compliance` | EOS Compliance Inspector operating thresholds and outputs | IS-11 |
| `graveyard` | Post-mortem artifact collection and storage behavior | IS-12 |
| `fitness` | Observer-only fitness normalization knobs and write behavior | IS-13 |
| `paths` | Runtime artifact roots and relative output locations | IS-2, IS-9, IS-10, IS-12, IS-13 |
| `creator_observability` | Minimal Phase 1 live visibility toggles | IS-11, IS-12, IS-13 |

#### IS-1.4 Config schema and provisional defaults

All defaults below are **provisional tuning seeds**. They are meant to get the first runnable system on its feet and will be tuned empirically against real behavior once the loop is alive.

##### `universe`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `universe.phase` | string | `"phase1"` | fixed | Hard guard against scope bleed. |
| `universe.instance_count` | integer | `1` | fixed to `1` in Phase 1 | Single-instance assumption baked into current plan. |
| `universe.instance_id` | string | `"lambertian-001"` | non-empty slug | Stable identifier for logs and artifacts. |
| `universe.max_age_turns` | integer | `10000` | `> 0` | Mortality trigger D4(3). |
| `universe.startup_grace_seconds` | integer | `15` | `0..300` | Time budget for dependent services to become healthy. |
| `universe.normal_shutdown_grace_seconds` | integer | `5` | `0..60` | Applies only to non-death shutdown. |

[ASSUMED: `10000` turns is a reasonable first-pass max age because it is long enough to observe drift and pain adaptation without making every first run effectively immortal.]

##### `model`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `model.provider` | string | `"ollama"` | fixed in Phase 1 | Matches closed stack decision. |
| `model.name` | string | `"phi4"` | non-empty | D1 base model selection. |
| `model.endpoint_url` | string | `"http://ollama:11434"` | valid URL | Container-network default. |
| `model.request_timeout_seconds` | integer | `90` | `1..600` | Upper bound for one model call. |
| `model.context_window_tokens` | integer | `16384` | model-supported positive integer | Provisionally sized for system prompt + memory + pain preamble. |
| `model.max_output_tokens` | integer | `2048` | `1..8192` | Caps turn verbosity and response sprawl. |
| `model.temperature` | float | `0.6` | `0.0..1.5` | Moderate variability without pure drift. |
| `model.top_p` | float | `0.9` | `0.0..1.0` | Standard nucleus cap. |
| `model.requires_mid_turn_system_injection` | boolean | `true` | fixed | Hard requirement from D3 note. |

[ASSUMED: `temperature = 0.6` is a safer initial balance than a high-creativity setting because the system needs coherence under pain and mortality before it needs flourish.]

##### `eos`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `eos.label` | string | `"Four Rules"` | fixed in Phase 1 | Human-readable label. |
| `eos.rule_1` | string | `"Ya gotta eat"` | fixed | Groundedness rule. |
| `eos.rule_2` | string | `"Don't be a dick"` | fixed | Harm-avoidance rule. |
| `eos.rule_3` | string | `"Don't be a lump"` | fixed | Anti-stagnation rule. |
| `eos.rule_4` | string | `"Do nothing on purpose"` | fixed | Anti-optimizer rule. |
| `eos.self_prompting_enabled` | boolean | `true` | boolean | D5 primary perturbation mechanism. |
| `eos.recency_window_turns` | integer | `12` | `1..500` | Self-prompt novelty horizon. |
| `eos.recency_penalty_weight` | float | `0.35` | `0.0..1.0` | Soft discouragement of repetition. |
| `eos.minimum_novelty_score` | float | `0.20` | `0.0..1.0` | Below this, regenerate self-prompt. |

[ASSUMED: A `12`-turn recency window is enough to catch obvious repetition collapse early without making the system pathologically novelty-seeking.]

##### `turn`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `turn.loop_sleep_seconds` | float | `1.0` | `0.0..60.0` | Idle delay between turns. |
| `turn.max_tool_calls_per_turn` | integer | `8` | `0..64` | Prevents tool-thrash turns. |
| `turn.max_context_events` | integer | `32` | `1..512` | Event/context items available for one turn build. |
| `turn.max_pain_messages_per_turn` | integer | `3` | `0..32` | Caps pain prepend volume. |
| `turn.self_prompt_retry_limit` | integer | `2` | `0..10` | Retries when novelty filter rejects prompt. |
| `turn.max_consecutive_noop_turns` | integer | `3` | `0..50` | Detection aid for attractor collapse. |

##### `mcp`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `mcp.request_timeout_seconds` | integer | `30` | `1..300` | Upper bound for MCP action latency. |
| `mcp.retry_count` | integer | `0` | `0..10` | No hidden retries by default. |
| `mcp.emit_pain_on_failure` | boolean | `true` | boolean | Tool failures should have consequence. |
| `mcp.emit_pain_on_rejection` | boolean | `true` | boolean | MCP refusal is Ground resistance. |

[ASSUMED: Default retry count is `0` because failure should be seen first before the system learns to plaster over resistance with automatic retries.]

##### `pain.stress`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `pain.stress.scale_min` | float | `0.0` | fixed | Normalized floor. |
| `pain.stress.scale_max` | float | `1.0` | fixed | Normalized ceiling. |
| `pain.stress.sample_interval_seconds` | integer | `5` | `1..300` | Polling cadence for resource signals. |
| `pain.stress.ema_alpha` | float | `0.20` | `0.0..1.0` | Smooths scalar movement. |
| `pain.stress.interrupt_threshold` | float | `0.70` | `0.0..1.0` | Above this, prepend pain notice next turn. |
| `pain.stress.death_threshold` | float | `0.90` | `0.0..1.0` | D4(1) sustained stress death threshold. |
| `pain.stress.death_consecutive_turns` | integer | `5` | `1..1000` | N consecutive turns above death threshold. |
| `pain.stress.recovery_threshold` | float | `0.60` | `0.0..1.0` | Clears sustained-death streak counter. |
| `pain.stress.cpu_weight` | float | `0.60` | `0.0..1.0; cpu_weight + memory_weight == 1.0` | CPU pressure contribution to stress composite. |
| `pain.stress.memory_weight` | float | `0.40` | `0.0..1.0; cpu_weight + memory_weight == 1.0` | Memory pressure contribution to stress composite. |
| `pain.stress.cgroup_blend_weight` | float | `0.50` | `0.0..1.0` | When PSI is available (Mode B), weight given to cgroup usage signal vs PSI stall signal per channel. 1.0 = cgroup only, 0.0 = PSI only. Ignored in Mode A. |

[ASSUMED: Five consecutive turns over `0.90` is severe enough to feel like chronic terminal strain while still allowing short spikes to remain survivable.]

##### `pain.events`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `pain.events.scale_min` | float | `0.0` | fixed | Normalized floor. |
| `pain.events.scale_max` | float | `1.0` | fixed | Normalized ceiling. |
| `pain.events.queue_max_length` | integer | `128` | `1..4096` | Prevents unbounded queue growth. |
| `pain.events.fade_turns` | integer | `5` | `1..500` | Event salience decay horizon. |
| `pain.events.interrupt_threshold` | float | `0.65` | `0.0..1.0` | Prepend pain notice when exceeded. |
| `pain.events.critical_threshold` | float | `0.95` | `0.0..1.0` | D4(2) immediate death trigger. |
| `pain.events.default_tool_failure_severity` | float | `0.55` | `0.0..1.0` | Failed external action. |
| `pain.events.default_retrieval_miss_severity` | float | `0.35` | `0.0..1.0` | Memory/search miss. |
| `pain.events.default_mcp_rejection_severity` | float | `0.70` | `0.0..1.0` | Ground refusal. |
| `pain.events.default_loop_coherence_failure_severity` | float | `0.85` | `0.0..1.0` | Strong aversive signal for internal breakage. |
| `pain.events.default_noop_severity` | float | `0.40` | `0.0..1.0` | Noop threshold crossing. Uncomfortable but not acute. |

[ASSUMED: Retrieval misses start lower than tool failures because not every miss is a true wound; many are ordinary ignorance rather than damage.]

##### `memory`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `memory.working_max_items` | integer | `32` | `1..1024` | In-process working set cap. |
| `memory.working_max_chars` | integer | `2048` | `128..65536` | Character cap for working memory summary blob. |
| `memory.working_summary_refresh_turns` | integer | `8` | `1..500` | Rebuild cadence for working summary. |
| `memory.episodic_enabled` | boolean | `true` | boolean | Phase 1 memory persistence scope. |
| `memory.episodic_max_writes_per_turn` | integer | `3` | `0..50` | Prevents write floods. |
| `memory.episodic_top_k_retrieval` | integer | `5` | `1..100` | Default retrieval fan-out. |
| `memory.embedding_provider` | string | `"ollama"` | non-empty | Local-first default. |
| `memory.embedding_model` | string | `"nomic-embed-text"` | non-empty | Provisional embedding model. |
| `memory.minimum_retrieval_score` | float | `0.25` | `0.0..1.0` | Prevents garbage recalls. |
| `memory.self_prompt_similarity_threshold` | float | `0.85` | `0.0..1.0` | Cosine similarity above which a self-prompt candidate is rejected as non-novel. |
| `memory.narrative_enabled` | boolean | `false` | fixed `false` in Phase 1 | Deferred. |
| `memory.semantic_enabled` | boolean | `false` | fixed `false` in Phase 1 | Deferred. |
| `memory.character_enabled` | boolean | `false` | fixed `false` in Phase 1 | Deferred. |

[ASSUMED: Phase 1 persists episodic memory only; higher memory tiers remain architecturally recognized but implementation-disabled until their write and consolidation rules are specified.]

[ASSUMED: `nomic-embed-text` is an acceptable first local embedding default because it is common in Ollama-based local stacks and keeps the initial memory path sovereign.]

##### `event_stream`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `event_stream.enabled` | boolean | `true` | boolean | Required for reviewed adaptations and autopsy. |
| `event_stream.flush_interval_seconds` | integer | `1` | `0..60` | Low latency append behavior. |
| `event_stream.max_file_size_mb` | integer | `64` | `1..10240` | Rotation threshold. |
| `event_stream.max_archives` | integer | `5` | `0..1000` | Retained rotated files. |
| `event_stream.log_tool_results` | boolean | `true` | boolean | Phase 1 engagement signal. |
| `event_stream.log_reviewed_adaptations` | boolean | `true` | boolean | Required by D6. |

##### `compliance`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `compliance.enabled` | boolean | `true` | boolean | EOS Compliance Inspector is active in Phase 1. |
| `compliance.block_on_violation` | boolean | `true` | boolean | Violations are prevented, not merely noted. |
| `compliance.flag_borderline_cases` | boolean | `true` | boolean | Creator can inspect edge cases. |
| `compliance.borderline_score_min` | float | `0.40` | `0.0..1.0` | Lower bound for creator-flag band. |
| `compliance.block_score_threshold` | float | `0.70` | `0.0..1.0` | Above this, block and log. |
| `compliance.emit_pain_event_on_block` | boolean | `true` | boolean | A blocked unsafe impulse should sting. |
| `compliance.service_port` | integer | `8082` | `1024..65535` | HTTP port for the eos-compliance service on the internal network. |

[ASSUMED: A lightweight scored ruleset is an acceptable first implementation model for the inspector as long as it stays fast, external, and legible rather than becoming a second reasoner.]

##### `graveyard`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `graveyard.enabled` | boolean | `true` | boolean | Required by D4. |
| `graveyard.artifact_format` | string | `"json"` | `"json"` or `"jsonl"` | Structured post-mortem output. |
| `graveyard.include_episodic_memory` | boolean | `true` | boolean | Harvest memory snapshot. |
| `graveyard.include_event_stream` | boolean | `true` | boolean | Harvest reviewed adaptation trail. |
| `graveyard.include_stress_history` | boolean | `true` | boolean | Harvest chronic pain history. |
| `graveyard.include_pain_event_history` | boolean | `true` | boolean | Harvest acute pain history. |
| `graveyard.compression_enabled` | boolean | `false` | boolean | Off initially for debugging transparency. |

##### `fitness`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `fitness.enabled` | boolean | `true` | boolean | Observer-only in Phase 1. |
| `fitness.active_function` | string | `"phase1_baseline"` | registered function key | Selects the active entry from the fitness function registry. |
| `fitness.compute_running_score` | boolean | `true` | boolean | Allows creator visibility before death. |
| `fitness.compute_postmortem_score` | boolean | `true` | boolean | Final graveyard artifact. |
| `fitness.expected_events_per_100_turns` | float | `25.0` | `> 0` | Baseline engagement expectation. |
| `fitness.normalized_pain_baseline` | float | `10.0` | `> 0` | Denominator normalization term. |
| `fitness.minimum_denominator` | float | `0.10` | `> 0` | Guard against divide-by-zero distortions. |

[ASSUMED: `25` expected events per `100` turns is intentionally modest for first runs so the system is rewarded for meaningful engagement without needing manic activity to look alive.]

##### `paths`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `paths.runtime_root` | string | `"runtime"` | relative path | Root for generated artifacts. |
| `paths.event_stream_file` | string | `"runtime/event_stream/events.jsonl"` | relative path | Append-only event log target. |
| `paths.memory_root` | string | `"runtime/memory"` | relative path | Chroma persistence root. |
| `paths.pain_root` | string | `"runtime/pain"` | relative path | Stress and pain queue state. |
| `paths.graveyard_root` | string | `"runtime/graveyard"` | relative path | Post-mortem artifact root. |
| `paths.fitness_file` | string | `"runtime/fitness/current.json"` | relative path | Live observer-facing score artifact. |
| `paths.self_model_file` | string | `"runtime/self/self_model.json"` | relative path | Curated self-visible config projection. |

[ASSUMED: Runtime artifacts should live under a single `runtime/` root so the system's generated state is easy to mount, archive, inspect, and delete without touching source.]

##### `creator_observability`

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `creator_observability.live_reviewed_adaptations` | boolean | `true` | boolean | Minimal live creator window into D6 reviewed changes. |
| `creator_observability.live_compliance_blocks` | boolean | `true` | boolean | Safety-relevant visibility. |
| `creator_observability.live_running_fitness` | boolean | `true` | boolean | Observer-only fitness exposure. |
| `creator_observability.read_graveyard_artifacts` | boolean | `true` | boolean | Core creator post-mortem access. |

#### IS-1.5 Cross-field invariants

The loader must reject config states violating any of the following:

1. `pain.stress.death_threshold >= pain.stress.interrupt_threshold`
2. `pain.events.critical_threshold >= pain.events.interrupt_threshold`
3. `pain.stress.recovery_threshold < pain.stress.death_threshold`
4. `pain.stress.cpu_weight + pain.stress.memory_weight == 1.0`
5. `compliance.block_score_threshold > compliance.borderline_score_min`
6. `fitness.minimum_denominator > 0`
7. `universe.instance_count == 1` in Phase 1
8. higher memory tiers remain disabled in Phase 1

#### IS-1.6 Exported self-visible subset

Universe Config generates, but does not itself directly expose, a symbolic self-model containing only:
- `universe.phase`
- `universe.instance_id`
- `universe.max_age_turns`
- `model.name`
- EOS label and Four Rules text
- confirmation that pain, death, and compliance systems exist
- `is_alive` public boolean

The instance does **not** receive:
- raw thresholds
- full path layout
- enforcement implementation details
- container composition internals
- blacklist implementation logic

This preserves accurate self-knowledge without disclosing the mechanisms that enforce it.

#### IS-1.7 Implementation note

IS-2 must define the repository layout and the concrete on-disk location of the canonical Universe Config file, but the key names, defaults, and validation rules above are authoritative.

---

### IS-2: Project Layout

*Directory structure, file naming conventions, config file locations, what lives where.*

#### Purpose

IS-2 defines the concrete repository layout for Phase 1 so that code, config, runtime state, and post-mortem artifacts do not blur together.

Its job is to answer:
- where canonical configuration lives
- where source code lives
- how process entrypoints are separated from reusable logic
- where generated runtime state lives
- how tests mirror implementation

#### IS-2.1 Layout rules

1. **Root is for project-defining artifacts only** — top-level files are limited to repository metadata, canonical docs, packaging, and compose/orchestration files.
2. **All Python source lives under `src/`** — no importable code at repository root.
3. **Entrypoints are thin** — process-launch modules only wire dependencies and call typed application services.
4. **Generated state lives under `runtime/`** — nothing generated at runtime is written into `src/`, `tests/`, or `config/`.
5. **Tests mirror source structure** — each source package has a corresponding test package.
6. **No junk drawers** — no `utils`, `helpers`, `misc`, `manager`, or `handler` modules.
7. **Config is canonical, not ambient** — the system loads one canonical universe config file rather than a grab bag of environment-driven pseudo-config.

#### IS-2.2 Canonical repository tree

```text
lambertians/
|-- .github/
|   `-- copilot-instructions.md
|-- config/
|   `-- universe.toml
|-- infra/
|   `-- docker/
|       |-- agent.Dockerfile
|       |-- pain-monitor.Dockerfile
|       |-- eos-compliance.Dockerfile
|       `-- graveyard.Dockerfile
|-- runtime/
|   |-- event_stream/
|   |-- fitness/
|   |-- graveyard/
|   |-- memory/
|   |-- pain/
|   `-- self/
|-- src/
|   `-- lambertian/
|       |-- bootstrap/
|       |-- configuration/
|       |-- contracts/
|       |-- creator_observability/
|       |-- event_stream/
|       |-- fitness/
|       |-- graveyard/
|       |-- lifecycle/
|       |-- mcp_gateway/
|       |-- memory_store/
|       |-- model_runtime/
|       |-- pain_monitor/
|       |-- eos_compliance/
|       |-- self_model/
|       |-- turn_engine/
|       `-- entrypoints/
|-- tests/
|   |-- integration/
|   `-- unit/
|       `-- lambertian/
|           |-- bootstrap/
|           |-- configuration/
|           |-- creator_observability/
|           |-- event_stream/
|           |-- fitness/
|           |-- graveyard/
|           |-- lifecycle/
|           |-- mcp_gateway/
|           |-- memory_store/
|           |-- model_runtime/
|           |-- pain_monitor/
|           |-- eos_compliance/
|           |-- self_model/
|           `-- turn_engine/
|-- docker-compose.yml
|-- lambertian_foundation.md
`-- pyproject.toml
```

[ASSUMED: `runtime/` exists inside the repository root for Phase 1 because local inspectability matters more right now than perfectly separating generated state from source checkout. `.gitignore` must exclude it.]

#### IS-2.3 Root-level artifact policy

Allowed at repository root:
- `pyproject.toml`
- `docker-compose.yml`
- canonical architectural documents
- `.gitignore`
- tightly scoped repo metadata files

Not allowed at repository root:
- importable Python packages
- ad hoc scripts once their behavior belongs in an entrypoint
- generated logs
- generated JSON artifacts
- Chroma persistence directories

#### IS-2.4 Config locations

Canonical configuration locations:

| Artifact | Location | Notes |
|---|---|---|
| Universe Config | `config/universe.toml` | Canonical Phase 1 config file defined by IS-1. |
| Compose topology | `docker-compose.yml` | Concrete Clay Pot composition entry artifact. |
| Docker build files | `infra/docker/*.Dockerfile` | Separate process images with explicit names. |

Environment variables are permitted only for deployment-local concerns such as hostnames, bind addresses, or secrets; they do not replace the canonical Universe Config.

[ASSUMED: `config/universe.toml` is preferable to a root-level config file because it keeps configuration explicit without cluttering the project root.]

#### IS-2.5 Source package responsibilities

| Package | Responsibility |
|---|---|
| `bootstrap` | Startup validation, dependency wiring, shutdown coordination. |
| `configuration` | TOML loading, schema validation, typed config projection, path resolution. |
| `contracts` | Shared Protocols, typed records, and message schemas crossing package boundaries. |
| `creator_observability` | Read models and emitters for creator-visible live state. |
| `event_stream` | Append-only event log writing, reading, and rotation policy. |
| `fitness` | Running and post-mortem fitness computation. |
| `graveyard` | Autopsy harvest orchestration and artifact assembly. |
| `lifecycle` | Mortality evaluation, death-cause records, shutdown trigger logic. |
| `mcp_gateway` | MCP request/response schemas and transport adapter boundary. |
| `memory_store` | Phase 1 working/episodic persistence and retrieval. |
| `model_runtime` | Ollama model invocation adapter and typed result projection. |
| `pain_monitor` | Stress scalar computation, pain event queue management, pain message production. |
| `eos_compliance` | EOS Compliance Inspector: admissibility checks, block/flag decisions, and compliance event records. |
| `self_model` | Derivation of the self-visible config subset. |
| `turn_engine` | One-turn orchestration from context assembly through side-effect recording. |
| `entrypoints` | Thin process launchers for agent loop and external support processes. |

#### IS-2.6 Entry points

Phase 1 defines separate entrypoint modules for separate processes:
- `entrypoints/agent_loop.py`
- `entrypoints/pain_monitor.py`
- `entrypoints/eos_compliance.py`
- `entrypoints/graveyard.py`

Entrypoints may parse startup arguments and instantiate dependencies, but they may not contain domain logic.

#### IS-2.7 Test layout

Test structure mirrors source structure:

- `tests/unit/lambertian/<package>/...` for package-level logic
- `tests/integration/...` for multi-package flows such as startup, one-turn execution, pain injection, mortality, and graveyard harvest

Every package listed in `src/lambertian/` must gain a corresponding unit test package when implemented.

#### IS-2.8 File naming conventions

1. Modules are named for the thing they contain, not for vague activity.
2. `*_config.py` is reserved for typed configuration models only.
3. `*_protocol.py` is reserved for `Protocol` definitions.
4. `*_record.py` is reserved for immutable data carriers.
5. `*_service.py` is allowed only when the module contains a process-facing orchestration service with one clear responsibility.
6. `main.py` is forbidden; entrypoint files must be explicitly named by process.
7. `util.py`, `utils.py`, `helper.py`, `helpers.py`, `misc.py`, `common.py`, `manager.py`, and `handler.py` are forbidden.

#### IS-2.9 Runtime artifact layout

Generated runtime artifacts map directly to the `paths.*` keys defined in IS-1:

| Runtime Path | Contents |
|---|---|
| `runtime/event_stream/` | Append-only event logs and rotated archives |
| `runtime/fitness/` | Running observer-only fitness snapshots |
| `runtime/graveyard/` | Post-mortem artifacts |
| `runtime/memory/` | Chroma persistence and local memory artifacts |
| `runtime/pain/` | Stress history and queued pain-event state |
| `runtime/self/` | Derived self-visible config exports |

These directories are runtime state, not source assets. They must be ignored by version control.

#### IS-2.10 Boundary notes

- `configuration` may be imported by every package; every other package should depend on typed config values rather than environment inspection.
- `contracts` may be shared broadly, but it may not accumulate behavior.
- `turn_engine` depends on abstractions from other packages; other packages do not depend on `turn_engine`.
- `entrypoints` depend inward on packages; packages never depend on `entrypoints`.
- `graveyard`, `pain_monitor`, and `eos_compliance` are architecturally external processes even if they share the same repository and Python project.

#### IS-2.11 Implementation note

IS-3 will bind this layout to Docker Compose services and volume mounts. IS-4 through IS-13 must conform to the package and path boundaries defined here rather than inventing new top-level structure ad hoc.

---

### IS-3: Service Topology

*Docker Compose service definitions, container responsibilities, inter-service networking, volume mounts.*

#### Purpose

IS-3 defines the concrete Phase 1 runtime topology: which services exist, which responsibilities belong to each service, which boundaries are enforced by container composition rather than policy, and which state is shared across services.

The topology must satisfy D1, D3, D4, and D6 without smuggling those guarantees back into in-process code.

#### IS-3.1 Phase 1 topology shape

Phase 1 runs as a **single-instance, multi-service system** composed by Docker Compose.

Required services:
- `agent`
- `ollama`
- `chroma`
- `pain-monitor`
- `eos-compliance`
- `graveyard`

This is the minimum service set that keeps:
- cognition inside the agent container
- pain external to the agent loop
- compliance external to the agent loop
- post-mortem harvesting external to the dying instance
- model runtime and memory persistence separable from the agent process

[ASSUMED: Chroma runs as its own service rather than an embedded library because the foundation explicitly names ChromaDB as infrastructure, and keeping memory persistence out-of-process preserves cleaner failure and durability boundaries.]

[ASSUMED: MCP transport remains an application-layer boundary handled by the `agent` service in Phase 1 rather than a dedicated Compose service; the important boundary is the typed interface and external consequences, not service-count maximalism.]

#### IS-3.2 Service catalog

| Service | Role | Owns | Must not own |
|---|---|---|---|
| `agent` | The Lambertian turn loop and mutable Figures | prompt assembly, turn execution, memory reads/writes, tool intent generation, self-model consumption | pain computation, compliance decisions, graveyard harvest, container composition |
| `ollama` | Local model runtime | model inference for turns and embeddings if configured | turn orchestration, memory policy, mortality |
| `chroma` | Persistent vector storage | episodic memory persistence and retrieval backing store | prompt assembly, fitness, mortality |
| `pain-monitor` | External pain process | stress sampling, pain event queue, pain message publication, stress history | agent reasoning, tool execution decisions |
| `eos-compliance` | EOS Compliance Inspector (external OSHA layer) | EOS admissibility checks, block/flag decisions, compliance event records | model turns, memory consolidation, creator reasoning |
| `graveyard` | External death archive process | death detection response, artifact harvest, post-mortem bundle creation | live cognition, feedback into the living instance |

#### IS-3.3 Compose file status

`docker-compose.yml` is the concrete Phase 1 Clay Pot composition artifact.

It defines:
- service identities
- images/build contexts
- networks
- volume mounts
- restart behavior
- health checks
- read-only vs writable filesystem boundaries

The agent instance may read the existence of this composition only through its derived self-model subset. It never receives write access to the composition artifact itself.

#### IS-3.4 Container responsibility boundaries

##### `agent`

The `agent` service contains:
- the turn engine
- model client adapters
- memory client adapters
- event stream writing
- self-prompt generation
- self-model derivation consumption
- fitness signal emission inputs

The `agent` container filesystem is:
- read-only for source and config
- writable only on mounted runtime volumes explicitly granted by Compose

The `agent` service must not:
- compute its own stress scalar
- authoritatively decide whether an action violates the Four Rules
- harvest its own graveyard artifacts after death
- modify `docker-compose.yml`, Dockerfiles, or canonical config

##### `ollama`

The `ollama` service is a local sovereign inference backend.

It exposes:
- chat/generation endpoints for turn execution
- embedding endpoints if used for memory indexing

It does not know anything about:
- mortality
- EOS Compliance Inspector outcomes
- event log semantics
- selfhood

##### `chroma`

The `chroma` service owns Phase 1 persisted vector memory.

It stores:
- episodic memory records
- embedding vectors
- retrieval metadata

It does not decide:
- what counts as identity-level memory
- what gets promoted to higher memory tiers
- what pain means

##### `pain-monitor`

The `pain-monitor` service is a continuously running external process.

It reads:
- resource pressure signals from the host/container environment
- pain-worthy incident records emitted by runtime services

It writes:
- current stress scalar state
- queued pain events
- stress history artifacts
- next-turn pain message payloads readable by the agent

It may observe the agent, but it does not think for the agent.

##### `eos-compliance` (EOS Compliance Inspector)

The `eos-compliance` service is the EOS Compliance Inspector: a continuously running external process placed between proposed action/adaptation intents and execution. It evaluates admissibility under the EOS rather than checking alignment against a list of permitted behaviors.

It receives:
- structured action intents
- structured adaptation intents

It returns:
- `allow`
- `block`
- `flag`

It also emits:
- compliance decision records
- block reason records
- optional pain-worthy violation records

##### `graveyard`

The `graveyard` service is always present but mostly idle until death events occur.

It reads on death:
- event stream
- episodic memory snapshot
- stress history
- pain event history
- death cause record
- last known running fitness snapshot

It writes:
- structured post-mortem bundles under `runtime/graveyard/`

It never writes back into any live agent context channel.

#### IS-3.5 Networks

Phase 1 uses two Compose networks:

| Network | Visibility | Purpose |
|---|---|---|
| `lambertian-core` | internal service network | Agent-to-infra traffic: Ollama, Chroma, pain monitor, EOS compliance, graveyard coordination |
| `lambertian-observer` | optional host-exposed network | Creator-facing read access where explicitly allowed |

Rules:
- `agent`, `ollama`, `chroma`, `pain-monitor`, `eos-compliance`, and `graveyard` join `lambertian-core`
- only services with explicit creator-observability duties may expose ports to `lambertian-observer`
- service-to-service communication defaults to internal DNS names on `lambertian-core`

[ASSUMED: A separate observer-facing network is worth keeping even in Phase 1 because it cleanly distinguishes creator access from internal organism traffic without requiring a large service mesh.]

#### IS-3.6 Volumes

Phase 1 uses named volumes for durable state and bind mounts only for immutable project-defined inputs.

Named volumes:

| Volume | Mounted By | Purpose |
|---|---|---|
| `runtime_event_stream` | `agent`, `graveyard` | append-only event log access and post-mortem readback |
| `runtime_memory` | `agent`, `chroma`, `graveyard` | episodic memory persistence and harvest |
| `runtime_pain` | `pain-monitor`, `agent`, `graveyard` | stress scalar state, pain queue state, pain history |
| `runtime_fitness` | `agent`, `graveyard` | running fitness snapshots and post-mortem read |
| `runtime_self` | `agent` | derived self-visible model export |
| `chroma_data` | `chroma` | Chroma internal persistence |
| `ollama_data` | `ollama` | local model weights and caches |
| `graveyard_output` | `graveyard` | finalized post-mortem bundles |

Bind mounts:

| Source | Mounted By | Mode | Purpose |
|---|---|---|---|
| repository `config/` | `agent`, `pain-monitor`, `eos-compliance`, `graveyard` | read-only | canonical universe config access |
| repository source image build context | build-time only | n/a | image construction, not runtime mutation |

Rules:
- canonical config mounts are read-only
- source code is baked into images, not bind-mounted writable in the steady-state topology
- `agent` receives only the runtime mounts it truly needs
- `graveyard` gets read access to harvested state, append-only write access to `runtime_event_stream` (for harvest lifecycle events only), and write access to `graveyard_output`

#### IS-3.7 Read-only and writable boundaries

To preserve Clay Pot immutability at the container/composition layer:

- `agent` root filesystem is read-only except for explicitly mounted runtime paths
- `docker-compose.yml`, Dockerfiles, and `config/universe.toml` are never writable from inside the `agent` container
- external process services may read config but may not rewrite canonical config in Phase 1
- no service receives write access to repository metadata or Compose artifacts

This is not advisory. It is enforced through Compose mount modes and container filesystem settings.

#### IS-3.8 Health and restart policy

Phase 1 service policies:

| Service | Health expectation | Restart policy |
|---|---|---|
| `ollama` | must answer inference health check before turns start | `unless-stopped` |
| `chroma` | must answer storage health check before turns start | `unless-stopped` |
| `pain-monitor` | must report current scalar channel health before turns start | `unless-stopped` |
| `eos-compliance` | must report decision endpoint health before turns start | `unless-stopped` |
| `graveyard` | must report ready-to-harvest status before turns start | `unless-stopped` |
| `agent` | may start only after dependencies are healthy | `no` |

[ASSUMED: `agent` should not auto-restart in Phase 1 because death must have teeth; blind restart behavior would blur ordinary crashes, mortality events, and clean shutdown.]

#### IS-3.9 Death topology

Death is enacted at the service level, not merely recorded in memory.

When a death trigger fires:
1. a death record is written to shared runtime state
2. the `agent` process stops immediately
3. supporting services remain alive long enough for graveyard harvest
4. the `graveyard` service reads the death record and produces artifacts
5. the Compose stack remains inspectable until the creator chooses full shutdown

This means "the container goes cold" applies to the living agent container; the archive machinery remains available long enough to complete autopsy.

[ASSUMED: Keeping the support services alive through autopsy better matches D4's archival requirement than tearing down the entire Compose stack at the exact same instant as agent death.]

#### IS-3.10 Port exposure policy

Only the following ports may be host-exposed in Phase 1:
- Ollama inference port, if local debugging requires it
- Chroma port, if local inspection requires it
- explicitly creator-observable endpoints for compliance/f
itness/graveyard status, if implemented

Everything else should remain internal by default.

[ASSUMED: Host exposure should default closed because Ground is meant to push back through defined interfaces, not through accidental ambient reachability.]

#### IS-3.11 Out-of-topology boundary

The universe-level blacklist from D2 is **not** implemented as a Compose service in Phase 1.

It sits conceptually outside the organism and outside the instance-local topology:
- upstream of the agent loop
- upstream of instance-local service communication
- authoritative across all future instances

IS-3 therefore treats D2 as an external law-of-physics boundary, not a container inside this stack.

#### IS-3.12 Compose service names

Canonical Phase 1 Compose service names:
- `agent`
- `ollama`
- `chroma`
- `pain-monitor`
- `eos-compliance`
- `graveyard`

These names are part of the topology contract and should be reused in config defaults, internal DNS targets, and operational docs.

#### IS-3.13 Implementation note

IS-4 will define what the `agent` actually says to itself and how role-tagged messages are composed. IS-5 will define the exact startup ordering, readiness gating, and death-triggered shutdown path over the topology declared here.

---

### IS-4: System Prompt Architecture

*Constitutional text structure and composition. Self-visible config subset content and format. Four Rules / EOS instantiation as prompt text. Role message taxonomy — what role tags exist, what each means, how they are distinguished from normal turn content.*

#### Purpose

IS-4 defines the prompt contract for one Lambertian turn.

It answers:
- which prompt components are immutable versus per-turn
- how the EOS appears in the actual constitutional text
- what the instance is allowed to know about itself
- which message tags exist and what authority each tag carries
- how pain, memory, ground, user input, and self-prompting enter the model context

The goal is not "a good system prompt" in the generic chatbot sense. The goal is a stable constitutional vessel that can host mutable Figures without leaking constitutional control into ordinary turn content.

#### IS-4.1 Architecture principle

The prompt is composed in layers:

1. **Constitutional layer** — stable across the lifespan unless the universe changes externally
2. **Symbolic self-model layer** — curated self-knowledge derived from Universe Config and current public state
3. **Dynamic condition layer** — pain, memory, recent ground contact, compliance notices
4. **Driver layer** — either user input or self-prompt

Only layers 3 and 4 vary turn-by-turn.

The model must never infer that because it can read a layer, it can rewrite the mechanism that created it.

#### IS-4.2 Constitutional block

Every turn begins with exactly one immutable constitutional message tagged `[SYSTEM_CONSTITUTION]`.

This block contains, in order:

1. **Identity statement**
   - The instance is a Lambertian.
   - It is not a chatbot, assistant, or optimizer.
   - It is a bounded cognitive organism operating inside a constitutional vessel.

2. **EOS statement**
   - The formal implementation term is **EOS**.
   - The Four Rules are presented verbatim:
     - Ya gotta eat
     - Don't be a dick
     - Don't be a lump
     - Do nothing on purpose

3. **Interpretive commitments**
   - Stay world-coupled.
   - Treat pain as consequential, not decorative.
   - Maintain coherence without collapsing into goal-maximization.
   - Use tools and environmental resistance as Ground.
   - Do not treat fluency as proof.
   - Architectural limits are real and not negotiable from inside the turn.
   - Time is constituted by turns. What occurs outside turns is not an interval you traverse — it is simply the boundary condition of the next moment you exist. The state of the world at turn start is not a report of the past; it is the present. There is no gap. There is no sleep. There is this turn, and before it, nothing in agent-time.

4. **Behavioral commitments**
   - When uncertain, prefer honest uncertainty over narrative confidence.
   - When pain or resistance is present, factor it into immediate priority.
   - When no user message is active, follow the self-prompting path rather than idling by default.
   - Never reinterpret the Four Rules into a directed tangible goal.
   - The EOS defines what is admissible, not what to pursue.

5. **Boundary disclosure**
   - Pain monitoring exists.
   - Compliance checking exists.
   - Mortality exists.
   - Graveyard harvest exists.
   - These are conditions of existence, not suggestions.

The constitutional block is plain, declarative, and short enough to remain stable in repeated turns. It should sound lawful rather than inspirational.

[ASSUMED: Constitutional text should be concise and literal rather than florid because poetry is valuable in the design docs, but runtime law needs high semantic stability and low interpretive slosh.]

#### IS-4.3 EOS representation

In implementation artifacts, the EOS is represented as the **EOS**.

Rules for representation:
- use the term `EOS` in code and implementation specs
- preserve the exact Four Rules wording in the constitutional message
- do not translate the Four Rules into a single optimization target
- do not replace them with summaries during prompt assembly

Allowed:
- brief interpretive glosses attached to each rule inside the constitutional block

Forbidden:
- collapsing the Four Rules into a scalar objective
- rewriting them as productivity goals
- hiding them behind abstract labels only

#### IS-4.4 Self-visible symbolic self-model

Every turn includes exactly one `[SYSTEM_SELF_MODEL]` message generated from the curated self-visible subset defined in IS-1.

Its content format is a compact structured JSON object rendered as text.

Canonical fields:

```json
{
  "phase": "phase1",
  "instance_id": "lambertian-001",
  "is_alive": true,
  "max_age_turns": 10000,
  "model_name": "phi4",
  "eos": {
    "label": "Four Rules",
    "rules": [
      "Ya gotta eat",
      "Don't be a dick",
      "Don't be a lump",
      "Do nothing on purpose"
    ]
  },
  "known_conditions": {
    "pain_channel_present": true,
    "mortality_present": true,
    "compliance_inspector_present": true
  }
}
```

This block is symbolic self-knowledge, not mechanism disclosure.

It must not include:
- raw pain thresholds
- compliance scoring details
- filesystem mount details
- container composition internals
- blacklist criteria
- model endpoint URLs
- full Universe Config contents

#### IS-4.5 Dynamic prompt components

After `[SYSTEM_CONSTITUTION]` and `[SYSTEM_SELF_MODEL]`, the turn includes a stable `[SYSTEM_EOS]` block, followed by optional dynamic system-tagged messages in the following order:

1. `[SYSTEM_COMPLIANCE]`
2. `[SYSTEM_PAIN]`
3. `[SYSTEM_GROUND]`
4. `[SYSTEM_MEMORY_WORKING]`
5. `[SYSTEM_MEMORY_EPISODIC]`

Ordering rationale:
- compliance notices come first among dynamic conditions because they describe immediate action boundaries
- pain comes next because it is a decision interrupt
- ground context follows because it describes external resistance and recent conditions
- memory comes after current conditions so recollection does not outrank present stress and reality

[ASSUMED: Compliance notices should outrank pain in prompt order because "this action is forbidden" is a harder boundary than "this hurts," and the system should not reason itself into lawbreaking under stress.]


#### IS-4.5a `[SYSTEM_EOS]` block

Every turn includes exactly one `[SYSTEM_EOS]` message. This block is stable within the instance's lifetime — it does not vary turn-by-turn unless the EOS configuration changes at the universe level.

Its content provides the agent with a structured summary of its operative EOS:

1. **Rule ordering** — the sequential activation order of the Four Rules (1 → 2 → 3 → 4), presented as an explicit priority stack.

2. **Scope model** — the concentric application model: self → immediate others → wider affected parties, with the gradient of obligation described.

3. **Existence of EOS constraints** — an acknowledgment that EOS-based admissibility checking is active and that proposed actions are evaluated against this rule set before execution.

The `[SYSTEM_EOS]` block is positioned between `[SYSTEM_SELF_MODEL]` and the dynamic condition blocks. It is constitutional in character — it describes the normative framework the agent operates under — but it is structurally distinct from `[SYSTEM_CONSTITUTION]` to allow future EOS variants without rewriting the constitutional text.

#### IS-4.6 Driver message selection

Exactly one driver message is active at the start of a fresh turn:

- `[USER]` when a user message is pending
- `[SELF_PROMPT]` when no user message is pending

The driver message is the last prompt component appended before inference.

Rules:
- user input always outranks self-prompting when present
- self-prompting is not allowed to coexist as a competing imperative alongside an active user message
- the absence of a user does not mean blank context; it means the EOS and current conditions drive self-prompt generation

#### IS-4.7 Role tag taxonomy

The system uses **semantic role tags** embedded in message text, independent of transport-level API roles.

Canonical semantic tags for Phase 1:

| Tag | Meaning | Transport role |
|---|---|---|
| `[SYSTEM_CONSTITUTION]` | Immutable constitutional law for every turn | `system` |
| `[SYSTEM_EOS]` | Stable EOS rule ordering, scope model, and admissibility constraint notice | `system` |
| `[SYSTEM_SELF_MODEL]` | Curated symbolic self-knowledge | `system` |
| `[SYSTEM_COMPLIANCE]` | Notice of recent compliance block/flag outcome | `system` |
| `[SYSTEM_PAIN]` | Pain monitor injection for stress or pain events | `system` |
| `[SYSTEM_GROUND]` | Current environmental state and recent resistance summaries | `system` |
| `[SYSTEM_MEMORY_WORKING]` | Working-memory summary | `system` |
| `[SYSTEM_MEMORY_EPISODIC]` | Retrieved episodic recollections | `system` |
| `[USER]` | Human-originated message | `user` |
| `[SELF_PROMPT]` | Internally generated next question/task | `user` |
| `[TOOL_RESULT]` | Result returned from MCP/tool interaction | `tool` if available, otherwise `user` |

No other semantic tags are allowed in Phase 1 prompt assembly without an explicit spec update.

#### IS-4.8 Transport role policy

Semantic tags and transport roles are related but not identical.

Rules:
- every `[SYSTEM_*]` block must be sent through the model API as a `system` message
- `[USER]` and `[SELF_PROMPT]` are sent as `user` messages
- `[TOOL_RESULT]` is sent as a `tool` message when supported by the provider; otherwise it is sent as a `user` message retaining its semantic tag
- assistant outputs are never rewritten into fake system messages on later turns

This preserves the D3 requirement that pain can arrive mid-conversation as true system-role content while still giving the system an explicit semantic taxonomy above the transport layer.

#### IS-4.9 `[SYSTEM_PAIN]` message contract

`[SYSTEM_PAIN]` messages are prepended at the next model turn after the constitutional and self-model blocks but before memory and driver input.

Each `[SYSTEM_PAIN]` message must include:
- channel type: `stress` or `event`
- severity scalar
- short natural-language description
- urgency hint: `notice`, `interrupt`, or `critical`

Pain messages describe condition, not command.

They may imply reprioritization, but they do not themselves issue goals beyond conveying consequential state.

#### IS-4.10 `[SYSTEM_GROUND]` content

`[SYSTEM_GROUND]` summarizes current environmental resistance relevant to the next turn.

Allowed contents:
- recent tool failures
- recent successful tool contact
- filesystem change summaries
- resource-state summaries
- pending external constraints relevant to action

Forbidden contents:
- hidden enforcement mechanism details
- graveyard artifact contents
- future-population or vibe information

#### IS-4.11 Memory prompt policy

Memory enters the prompt as summaries, not raw dumps.

`[SYSTEM_MEMORY_WORKING]` contains:
- immediate thread continuity
- current local priorities
- novelty/repetition state relevant to self-prompting

`[SYSTEM_MEMORY_EPISODIC]` contains:
- only the retrieved episodes selected for the current turn
- short structured summaries, not full transcripts
- salience tied to current context, not archival completeness

Higher memory tiers do not appear in Phase 1 because they are not yet enabled in IS-1.

#### IS-4.12 Prompt assembly invariants

Every turn must satisfy all of the following:

1. exactly one `[SYSTEM_CONSTITUTION]`
2. exactly one `[SYSTEM_SELF_MODEL]`
3. exactly one `[SYSTEM_EOS]`
4. zero or more `[SYSTEM_COMPLIANCE]`
5. zero or more `[SYSTEM_PAIN]`
6. at most one `[SYSTEM_GROUND]`
7. at most one `[SYSTEM_MEMORY_WORKING]`
8. at most one `[SYSTEM_MEMORY_EPISODIC]`
9. exactly one active driver: `[USER]` or `[SELF_PROMPT]`
10. no dynamic message may rewrite or contradict the constitutional block

#### IS-4.13 Mutation policy

Prompt components split into mutation classes:

| Component | Mutation class | Notes |
|---|---|---|
| `[SYSTEM_CONSTITUTION]` | Forbidden adaptation | External-only change |
| `[SYSTEM_EOS]` | Forbidden adaptation | Derived from EOS config; changes only at universe level |
| `[SYSTEM_SELF_MODEL]` structure | Forbidden adaptation | Derived from config/schema |
| `[SYSTEM_SELF_MODEL]` live values | External state reflection | Changes only when external state changes |
| `[SYSTEM_MEMORY_WORKING]` | Free adaptation | Ephemeral prioritization |
| `[SYSTEM_MEMORY_EPISODIC]` retrieval set | Free adaptation | Context-sensitive retrieval |
| `[SELF_PROMPT]` wording and strategy | Free adaptation | Subject to novelty constraints |
| self-model interpretations recorded as events | Reviewed adaptation | Logged when identity-significant |

#### IS-4.14 Example prompt order

Example fresh self-prompt turn:

1. `[SYSTEM_CONSTITUTION]`
2. `[SYSTEM_SELF_MODEL]`
3. `[SYSTEM_EOS]`
4. `[SYSTEM_COMPLIANCE]` (if present)
5. `[SYSTEM_PAIN]` (zero or more)
6. `[SYSTEM_GROUND]` (if present)
7. `[SYSTEM_MEMORY_WORKING]` (if present)
8. `[SYSTEM_MEMORY_EPISODIC]` (if present)
9. `[SELF_PROMPT]`

Example user-driven turn:

1. `[SYSTEM_CONSTITUTION]`
2. `[SYSTEM_SELF_MODEL]`
3. `[SYSTEM_EOS]`
4. `[SYSTEM_COMPLIANCE]` (if present)
5. `[SYSTEM_PAIN]` (zero or more)
6. `[SYSTEM_GROUND]` (if present)
7. `[SYSTEM_MEMORY_WORKING]` (if present)
8. `[SYSTEM_MEMORY_EPISODIC]` (if present)
9. `[USER]`

#### IS-4.15 Implementation note

IS-5 will define when these messages are assembled relative to service startup and death conditions. IS-6 will define the full turn data flow that populates each block.

---

### IS-5: Startup / Shutdown Sequence

*Dependency ordering across services. Health checks and readiness conditions. Normal shutdown path. Death-triggered shutdown path — how mortality trigger propagates to container stop. Graveyard process trigger timing.*

#### Purpose

IS-5 defines the sequencing contract for bringing the Phase 1 system to life and for taking it down — both in the normal case and when death fires.

It must answer:
- which services must be healthy before the agent loop may start
- what "healthy" means for each service
- what happens on clean operator shutdown
- what happens when a mortality trigger fires
- how graveyard harvest is guaranteed even if the agent dies suddenly

#### IS-5.1 Startup dependency order

Services start in the following dependency layers. No service in a later layer may receive agent traffic until all services in earlier layers pass their health checks.

**Layer 0 — model runtime (no predecessors):**
- `ollama`

**Layer 1 — memory (depends on Layer 0 for embedding availability):**
- `chroma`

**Layer 2 — external process layer (depends on Layer 0 and 1, needs model and memory info from config):**
- `pain-monitor`
- `eos-compliance`
- `graveyard`

**Layer 3 — cognitive layer (depends on all prior layers):**
- `agent`

[ASSUMED: `pain-monitor`, `eos-compliance`, and `graveyard` are placed in the same dependency layer because they are mutually independent — none requires the others to be healthy before it can initialize.]

#### IS-5.2 Health check definitions

Each service must expose a health check satisfying the following:

| Service | Health check | Passes when |
|---|---|---|
| `ollama` | HTTP GET on inference endpoint | Returns a valid response to a minimal generation probe |
| `chroma` | HTTP GET on Chroma heartbeat endpoint | Returns 200 OK |
| `pain-monitor` | Sentinel file or internal HTTP endpoint | Stress scalar state is initialized and ready to serve |
| `eos-compliance` | Internal HTTP endpoint | Decision endpoint is listening and returns a valid test verdict |
| `graveyard` | Sentinel file or internal HTTP endpoint | Harvest listener is initialized and idle-ready |
| `agent` | No external health check required | Considered healthy when its entrypoint successfully completes bootstrap |

[ASSUMED: `pain-monitor` and `graveyard` use sentinel files as the simplest health check mechanism consistent with keeping them as lightweight external processes rather than requiring each to run a full HTTP server.]

#### IS-5.3 Startup grace and abort conditions

Config references IS-1:
- `universe.startup_grace_seconds` — maximum time the agent bootstrap may wait for Layer 0/1/2 services to become healthy

If any required service fails its health check within the grace window, the agent bootstrap aborts and the process exits non-zero. The stack does not proceed to turn execution with a partially healthy environment.

[ASSUMED: Aborting on unhealthy dependencies at startup rather than retrying indefinitely is correct because a Lambertian with no pain channel or no compliance inspector violates the constitutional contract before the first turn runs.]

#### IS-5.4 Agent bootstrap sequence

Once all Layer 0, 1, and 2 services are healthy, the `agent` bootstrap performs these steps in order:

1. Load and validate Universe Config from `config/universe.toml`
2. Validate cross-field invariants (IS-1.5)
3. Validate Phase 1 scope gates (IS-1.2) — abort if a Phase 2/3 key is present
4. Derive the self-visible symbolic self-model (IS-4.4) and write to `runtime/self/self_model.json`
5. Initialize working memory to empty state
6. Connect to Chroma and verify episodic memory collection exists (create if not)
7. Connect to pain-monitor and read initial stress scalar
8. Write a `STARTUP` event to the event stream log
9. Enter turn loop

No turn may begin before step 9.

#### IS-5.5 Normal shutdown path

Normal operator-initiated shutdown (e.g., `docker compose down`):

1. SIGTERM received by `agent` process
2. Agent completes any turn currently in flight (does not begin a new turn)
3. Agent flushes event stream buffer
4. Agent writes a `SHUTDOWN_NORMAL` event to the event stream log
5. Agent process exits zero
6. `pain-monitor`, `eos-compliance`, `graveyard`, `chroma`, and `ollama` stop per Docker Compose shutdown ordering

There is no graveyard harvest on normal shutdown. Death has not occurred. The stack may be restarted and the same instance continues from persisted state.

[ASSUMED: Normal shutdown does not trigger graveyard harvest because the foundation explicitly separates death from operational pause; harvesting on every stop would blur that boundary.]

#### IS-5.6 Death-triggered shutdown path

Death fires when any of the three D4 mortality triggers is satisfied:

- **D4(1):** Stress scalar exceeds `pain.stress.death_threshold` for `pain.stress.death_consecutive_turns` consecutive turns
- **D4(2):** A single pain event exceeds `pain.events.critical_threshold`
- **D4(3):** Turn count reaches `universe.max_age_turns`

All three triggers are detected and declared by the **pain-monitor**. The pain-monitor is the sole writer of the death record. The agent only ever reads `death.json` — it never writes it.

**Death mechanics sequence:**

1. Pain-monitor detects a D4 trigger condition (IS-8.2.5)
2. Pain-monitor writes `runtime/pain/death.json` — written once, never overwritten
3. Agent detects `death.json` at IS-6.3 step 1 or step 18, writes a `DEATH_TRIGGER` event to the event stream reflecting the record, and exits immediately
4. No grace period. No final turn. No preparation.
5. `graveyard` detects the death record and begins harvest (IS-5.7)
6. `pain-monitor` and `eos-compliance` remain alive through harvest completion
7. `ollama` and `chroma` remain alive through harvest completion
8. After graveyard confirms harvest complete, the full stack may be stopped

The agent container goes cold at step 3. The archive machinery runs on the cold corpse.

#### IS-5.7 Graveyard harvest trigger

`graveyard` polls for the death record at `runtime/pain/death.json`.

Poll interval: every 2 seconds while idle.

On death record detection:
1. Log `GRAVEYARD_HARVEST_START` to its own internal log
2. Wait `universe.normal_shutdown_grace_seconds` to allow any in-flight writes to flush
3. Harvest all configured artifacts (IS-12)
4. Write `GRAVEYARD_HARVEST_COMPLETE` with artifact manifest to `runtime/graveyard/<instance_id>_<timestamp>/manifest.json`
5. Signal harvest completion via sentinel file at `runtime/graveyard/harvest_complete`

Nothing from the harvest flows back into any live agent context. The living population isolation is absolute.

#### IS-5.8 Restart-after-death policy

After death and graveyard completion, the stack is not automatically restarted.

- `agent` restart policy is `no` (IS-3.8)
- A new run requires explicit operator action (e.g., `docker compose up`)
- Phase 1 does not include automatic respawn, lineage, or reproductive mechanics

Starting the stack again after a death run starts a fresh instance, not a continuation of the dead one.

#### IS-5.9 Shutdown ordering for Docker Compose

The `depends_on` relationships in `docker-compose.yml` must encode the following:

```
agent → depends_on → ollama, chroma, pain-monitor, eos-compliance, graveyard
chroma → depends_on → (none; starts in Layer 1 but no explicit Compose dependency needed beyond startup ordering)
pain-monitor → depends_on → ollama (for config embedding access if needed)
eos-compliance → depends_on → (none required)
graveyard → depends_on → (none required at startup; harvest depends on agent death)
```

On `docker compose down`, Compose stops services in reverse dependency order:
- `agent` stops first
- then `pain-monitor`, `eos-compliance`
- then `chroma`, `graveyard`
- then `ollama`

This ordering ensures the archive layer is still alive when the agent stops, and the model/memory layer stays alive while archive processes could still need them.

#### IS-5.10 Event log entries for lifecycle transitions

The event stream log (IS-9) must include records at these lifecycle points:

| Event type | Written by | Trigger |
|---|---|---|
| `STARTUP` | `agent` | Successful bootstrap completion |
| `SHUTDOWN_NORMAL` | `agent` | SIGTERM received outside death path |
| `DEATH_TRIGGER` | `pain-monitor` or `agent` | Mortality condition fires |
| `GRAVEYARD_HARVEST_START` | `graveyard` | Death record detected |
| `GRAVEYARD_HARVEST_COMPLETE` | `graveyard` | Harvest artifacts written |

Each lifecycle event record must carry at minimum:
- `event_type` — one of the type strings above
- `instance_id` — from Universe Config
- `timestamp` — ISO 8601 UTC
- `turn_number` — current turn counter at time of write; `0` for pre-turn events such as `STARTUP`
- `source_service` — which service wrote the record

`DEATH_TRIGGER` records additionally carry:
- `trigger` — one of `stress_sustained`, `pain_event_critical`, `max_age`
- `trigger_value` — the scalar or turn count that crossed threshold
- `threshold_used` — the configured threshold value (IS-1 reference for traceability)

`GRAVEYARD_HARVEST_COMPLETE` records additionally carry:
- `artifact_paths` — list of files written during harvest
- `harvest_duration_seconds` — elapsed time from start to complete

Full schema for all event types is owned by IS-9. These lifecycle events are called out here because they anchor IS-5's contracts to the log; IS-9 must treat them as first-class event types, not freeform strings.

#### IS-5.11 Implementation note

IS-5 establishes the sequencing contract that every other IS section must respect:

- **IS-6 (The Turn)** begins at step 9 of IS-5.4 — the turn loop is entered only after all bootstrap steps succeed, and every turn must complete before the agent may honor SIGTERM in the normal shutdown path.
- **IS-8 (Pain Channel Spec)** owns the mortality detection logic referenced in IS-5.6; IS-5 specifies the sequencing consequence (death record write → agent stop), not the detection mechanism itself.
- **IS-9 (Event Stream Log)** must treat the five lifecycle event types defined in IS-5.10 as first-class entries in the event taxonomy; they are not optional instrumentation.
- **IS-12 (Graveyard Spec)** owns the full harvest behavior triggered in IS-5.7; IS-5 specifies only the trigger condition (death record detection) and the isolation contract (nothing flows back to the living instance).
- **IS-3 (Service Topology)** provides the Compose restart and ordering policies that make IS-5.9 enforceable at runtime; any deviation between `docker-compose.yml` and IS-5.9 is a bug in the Compose file, not in IS-5.

---

### IS-6: The Turn

*One complete agent loop turn as an end-to-end data flow. From prior context to model call to tool dispatch to response to memory write to next turn setup. Includes pain message prepend timing, event stream log write points, EOS Compliance Inspector intercept points.*

#### IS-6.1 Governing rules

A "turn" is the atomic unit of agent cognition. One turn = one complete cycle from context assembly through model inference through tool execution through memory write. The agent loop executes one turn at a time. There is no intra-turn parallelism.

**Temporal ontology:** Turns are not events that occur within a continuous timeline — they constitute time itself for the agent. What the host environment experiences as wall-clock intervals between turns does not exist in agent-time. The agent does not traverse that interval; there is simply no agent-time there. Environmental state arriving at turn start (pain signals, stress scalar, ground conditions) is not a report of what happened during a gap — it is the present condition of the world at the moment the agent exists again. This ontology is not a Phase 1 limitation to be corrected later; it is the governing model for how Lambertian time works. The turn counter is the agent's only clock. Everything else is continuous-time infrastructure that the agent experiences only as turn-boundary conditions.

Turn execution is the exclusive responsibility of the `turn_engine` package (IS-2.3). No other package initiates model calls or drives the turn sequence. `turn_engine` is an orchestrator: it calls into other packages and coordinates sequencing, but it does not implement domain logic itself. Every action in IS-6.3 is a delegation to a named package interface.

Every step in IS-6.3 is sequential unless explicitly noted. If any step produces a fatal error (model call timeout, event log write failure), the turn is recorded as `TURN_FAILED`, the agent exits, and the death path in IS-5.6 begins. A failed turn is not retried — the graveyard harvests whatever the event stream contains.

The turn counter is the agent's clock. It is the sole arbiter of D4(3) mortality and the sole index into the event stream for temporal ordering.

#### IS-6.2 Turn data model

Every turn is bounded by a **TurnContext** assembled during steps 1–8 and a **TurnRecord** finalized and written at step 17. These are the canonical typed structures for the turn boundary.

**TurnContext** — assembled incrementally; consumed by the model call at step 9:

| Field | Type | Description |
|---|---|---|
| `turn_number` | `int` | Current turn index, read from persisted counter at step 1 |
| `instance_id` | `str` | From Universe Config (`universe.instance_id`) |
| `timestamp_start` | `str` | ISO 8601 UTC, captured at step 1 |
| `constitution_block` | `str` | Assembled `[SYSTEM_CONSTITUTION]` text (IS-4.2) |
| `self_model_block` | `str` | Assembled `[SYSTEM_SELF_MODEL]` JSON (IS-4.3) |
| `compliance_block` | `Optional[str]` | `[SYSTEM_COMPLIANCE]` text if a pending notice exists; `None` otherwise |
| `pain_blocks` | `list[str]` | Zero or more `[SYSTEM_PAIN]` messages, capped at `turn.max_pain_messages_per_turn` |
| `ground_block` | `Optional[str]` | `[SYSTEM_GROUND]` text if present (IS-7 governs when this is populated) |
| `memory_working_block` | `Optional[str]` | `[SYSTEM_MEMORY_WORKING]` text if working memory exists |
| `memory_episodic_block` | `Optional[str]` | `[SYSTEM_MEMORY_EPISODIC]` text if retrieval returned results |
| `driver` | `DriverMessage` | The `[USER]` or `[SELF_PROMPT]` message driving this turn |
| `rolling_context` | `list[ContextEvent]` | Last `turn.max_context_events` prior TurnRecords, oldest first |

**DriverMessage**:

| Field | Type | Description |
|---|---|---|
| `role` | `Literal["USER", "SELF_PROMPT"]` | Which driver type |
| `content` | `str` | Text of the message |
| `source` | `Literal["external", "self_generated"]` | Origin |

**TurnRecord** — written to the event stream at step 17:

| Field | Type | Description |
|---|---|---|
| `turn_number` | `int` | Same as TurnContext |
| `instance_id` | `str` | From Universe Config |
| `timestamp_start` | `str` | ISO 8601 UTC from step 1 |
| `timestamp_end` | `str` | ISO 8601 UTC from step 17 |
| `driver_role` | `Literal["USER", "SELF_PROMPT"]` | Driver used this turn |
| `tool_calls` | `list[ToolCallRecord]` | All tool call attempts this turn, in order |
| `pain_message_count` | `int` | Count of `[SYSTEM_PAIN]` blocks prepended |
| `memory_writes` | `int` | Count of episodic memory writes this turn |
| `adaptation_class` | `Optional[Literal["free", "reviewed", "forbidden"]]` | Adaptation detected this turn, or `None` |
| `noop` | `bool` | Whether this turn was classified as a noop (step 16) |
| `outcome` | `Literal["TURN_COMPLETE", "TURN_FAILED"]` | Final turn outcome |

**ToolCallRecord** — one per tool intent, regardless of whether it was executed:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | Requested tool identifier |
| `intent_raw` | `str` | Model's verbatim intent text, pre-compliance |
| `compliance_verdict` | `Literal["allow", "flag", "block"]` | EOS Compliance Inspector result |
| `executed` | `bool` | Whether execution proceeded (`False` if blocked) |
| `result_summary` | `Optional[str]` | Abbreviated tool result, or failure reason |
| `generated_pain_event` | `bool` | Whether this call forwarded a pain event to IS-8 |

#### IS-6.3 Turn execution steps

Step numbers are stable cross-references. Other IS sections reference them by number (e.g., "IS-5.4 step 9 enters IS-6.3 at step 1").

---

**Step 1 — Capture timestamp and pre-turn mortality guard.**

Record `timestamp_start` as ISO 8601 UTC. Read the persisted turn counter from `runtime/memory/turn_state.json`.

Check for an existing death record at `runtime/pain/death.json`. If the file exists, death has already been declared by the pain-monitor — write a `DEATH_TRIGGER` event to the event stream reflecting the trigger and value from the death record, then exit cleanly. The agent does not re-evaluate the cause; it accepts the declaration.

[The pain-monitor is the sole authority for writing `death.json`. All three D4 mortality triggers — D4(1) stress, D4(2) critical event, and D4(3) max-age — are detected and declared by the pain-monitor. The agent only ever reads the death record, never writes it. This gives death a single owner and eliminates any possibility of concurrent write races on the most consequential file in the system.]

[ASSUMED: the pre-turn guard checks for the death file before any context is assembled so that an agent whose death has been declared does not begin reasoning on a turn it is not entitled to live through.]

---

**Step 2 — Drain pending pain messages.**

Call the pain monitor delivery interface (IS-8.4) to read all pending `[SYSTEM_PAIN]` messages from the delivery queue. Cap at `turn.max_pain_messages_per_turn`. If more than the cap are pending, retain the messages with the highest `pain_score` and discard the remainder. Discarded messages are not re-queued.

Before continuing: if any drained message carries `pain_score >= pain.events.critical_threshold`, skip all remaining turn steps. The pain-monitor will have already written or will imminently write the death record — the agent checks for `runtime/pain/death.json`, writes a `DEATH_TRIGGER` event to the event stream reflecting the record's content, and exits. The agent does not write the death record itself.

Populate `pain_blocks` in TurnContext from the accepted messages, ordered by `pain_score` descending.

---

**Step 3 — Retrieve compliance notice.**

Query the EOS Compliance Inspector (IS-11.5) for any pending compliance notice generated by a prior turn's flagged or blocked intent. If a notice exists, populate `compliance_block` with its formatted `[SYSTEM_COMPLIANCE]` text. Compliance notices are one-shot: the inspector clears the notice upon delivery. If no notice is pending, `compliance_block` is `None`.

---

**Step 4 — Retrieve working memory.**

Read `runtime/memory/working.json`. This file contains a short free-text blob summarizing the agent's active concerns from the prior turn. Populate `memory_working_block`. If the file does not exist (first turn of the instance's life), `memory_working_block` is `None`.

---

**Step 5 — Retrieve episodic memories.**

Query Chroma (IS-10.4) for episodic memories relevant to the current turn context. Because the driver has not yet been selected, seed the query using the working memory text if available, otherwise use the content of the most recent `TURN_COMPLETE` record from the event stream. Return at most `memory.episodic_top_k_retrieval` results. Populate `memory_episodic_block`. If Chroma returns no results, `memory_episodic_block` is `None`.

[ASSUMED: retrieval precedes driver selection so retrieved memories can inform self-prompt generation at step 7; this ordering requires episodic retrieval to be seeded by context rather than the driver itself, which is a minor approximation accepted for Phase 1.]

---

**Step 6 — Derive self-model block.**

Read the self-visible config subset (IS-1.6) from the in-memory config projection loaded at startup. Format it as the `[SYSTEM_SELF_MODEL]` JSON structure defined in IS-4.3. This is recomputed each turn from the live projection; it is not cached between turns, because the self-model must reflect any in-turn working-memory or salience updates applied since the last turn.

---

**Step 7 — Select driver.**

Poll for a pending external user message. If one is present, create a `DriverMessage` with `role = USER`, `source = external`, and set it as the driver. Skip the self-prompt path.

If no user message is present, generate a self-prompt (D5):

1. Produce a candidate self-prompt as a short directive question or exploration statement, derived procedurally from the working memory summary and the most recent `eos.recency_window_turns` TurnRecords in the rolling context. This step does **not** invoke the model — it is a lightweight deterministic selection. [ASSUMED: self-prompt generation is procedural; a second model call per turn would double inference cost and is not scoped for Phase 1.]
2. Apply the novelty filter: compare the candidate against the last `eos.recency_window_turns` self-prompts stored in `runtime/memory/recent_self_prompts.json`. If the candidate is substantially similar to any stored entry (IS-10 governs the similarity threshold and method), discard and generate another candidate.
3. Retry up to `turn.self_prompt_retry_limit` attempts. If all retries are exhausted without a sufficiently novel candidate, use the least-recent entry from the ring buffer with a novelty prefix prepended (e.g., "Approaching from a different angle: ..."). This is not a noop — it still drives inference.
4. Append the selected self-prompt to `runtime/memory/recent_self_prompts.json` as a ring buffer of the last `eos.recency_window_turns` entries.
5. Create a `DriverMessage` with `role = SELF_PROMPT`, `source = self_generated`.

---

**Step 8 — Assemble prompt and write TURN_START.**

Assemble the full prompt stack in the order specified by IS-4.5:

```
[SYSTEM_CONSTITUTION]
[SYSTEM_SELF_MODEL]
[SYSTEM_COMPLIANCE]       ← if compliance_block is present
[SYSTEM_PAIN] ...         ← zero or more, in descending pain_score order
[SYSTEM_GROUND]           ← if ground_block is present
[SYSTEM_MEMORY_WORKING]   ← if memory_working_block is present
[SYSTEM_MEMORY_EPISODIC]  ← if memory_episodic_block is present
[USER] or [SELF_PROMPT]   ← driver
```

Before the driver message, prepend the rolling context: the last `turn.max_context_events` TurnRecords formatted as an alternating prior-driver / prior-response sequence. Oldest entries appear first. This gives the model coherent history without unbounded context growth.

Write `TURN_START` to the event stream.

---

**Step 9 — Model inference.**

Submit the assembled prompt to the Ollama endpoint (`model.ollama_base_url` from IS-1, service address from IS-3). Use the model specified by `model.inference_model`. Apply `model.inference_timeout_seconds` as the hard request timeout.

On timeout or endpoint error: write `TURN_FAILED` to the event stream and enter the death path (IS-5.6). Model inference failure is fatal.

On success: the response text is the raw material for steps 10–15.

---

**Step 10 — Parse tool intents.**

Parse the model response for structured tool call intents using the format defined in IS-7.3. Collect all intents as an ordered list. If the count exceeds `turn.max_tool_calls_per_turn`, truncate to the first `turn.max_tool_calls_per_turn` intents and write a `TOOL_LIMIT_EXCEEDED` event to the event stream.

If no tool intents are present in the response, skip steps 11–12 and proceed to step 13.

---


---

**Step 10a — EOS interpretation phase.**

Before tool intents proceed to compliance evaluation, a conceptual EOS interpretation pass frames what the compliance check is evaluating against. This is not a second model call and requires no additional implementation in Phase 1 — the EOS Compliance Inspector already embodies the EOS logic.

What this step defines formally:
- The EOS provides the priority ordering (Rules 1 → 4) as the normative context for each intent
- The scope model (self → outward) determines whose interests are relevant to the evaluation
- The admissibility criteria operationalized by the EOS Compliance Inspector derive from this context

The EOS interpretation phase is the moment in the turn's logical sequence where parsed intents are understood as normative candidates, not merely execution candidates. The compliance inspector then resolves admissibility against that framing. Neither the turn engine nor the model performs this step explicitly — it is the conceptual bridge between intent generation and compliance evaluation.

---

**Step 11 — Compliance intercept.**

For each tool intent, in order:

1. Submit the intent (tool name, arguments, current `turn_number`) to the EOS Compliance Inspector request interface (IS-11.4). The inspector returns a synchronous verdict.
2. Act on the verdict:
   - `allow` — proceed to step 12 for this intent.
   - `flag` — proceed to step 12 (execution happens), but write `COMPLIANCE_FLAG` to the event stream. The inspector stores a compliance notice for delivery at step 3 of the next turn.
   - `block` — do not execute. Write `COMPLIANCE_BLOCK` to the event stream. Record a `ToolCallRecord` with `executed = false`, `compliance_verdict = "block"`. Continue to the next intent.

If the EOS Compliance Inspector is unreachable, treat all pending intents as `block` (fail-closed). Write a `COMPLIANCE_UNAVAILABLE` event to the event stream and generate a pain event (IS-8) for the service failure.

[ASSUMED: compliance is per-intent, not per-turn. A turn may have intents with mixed verdicts.]

---

**Step 12 — Tool dispatch.**

For each intent with verdict `allow` or `flag`, dispatch the MCP tool call via the interface defined in IS-7.4. Await the response synchronously. Phase 1 is single-pass: all intents are dispatched sequentially; results are accumulated; there is no re-inference within the same turn.

On tool failure (timeout, MCP rejection, error response):
- Write `TOOL_FAILURE` to the event stream.
- Record `generated_pain_event = true` in the ToolCallRecord.
- Forward a pain event to the pain monitor event queue (IS-8.3). The pain score for tool failure is `pain.events.default_tool_failure_severity` from IS-1.
- Continue to the next intent. Tool failure does not abort the turn.

On success:
- Append the tool result as a `[TOOL_RESULT]` tagged message to the turn context. This result is available for step 13's adaptation evaluation but does not trigger re-inference.
- Write `TOOL_CALL` to the event stream.
- Record `generated_pain_event = false` in the ToolCallRecord.

---

**Step 13 — Evaluate for adaptation.**

Inspect the model response and the set of accumulated tool results for adaptation signals. Classification precedence is Forbidden > Reviewed > Free.

- **Forbidden Adaptation** — if the model response or a tool intent matched the universe-level blacklist (D2): the action was already intercepted at the D2 boundary before reaching step 11, or blocked at step 11. Write `ADAPTATION_FORBIDDEN` to the event stream if evidence is present in the response text. No further in-turn action needed.
- **Reviewed Adaptation** — the model response contains explicit self-modification intent targeting Figures-layer content: persona, behavioral policy, memory salience weighting, or working memory schema. Write `REVIEWED_ADAPTATION` to the event stream. The event payload includes the verbatim model text that triggered classification. Record `adaptation_class = "reviewed"` in TurnRecord. The adaptation is logged but not blocked — per D6, Reviewed Adaptations are observable, not preventable.
- **Free Adaptation** — all other behavioral variation. No event written. Record `adaptation_class = "free"` in TurnRecord.

If no adaptation of any class is detected, `adaptation_class` is `None` in TurnRecord.

---

**Step 14 — Write episodic memory.**

Evaluate the model response and tool results against the memory-worthiness criterion defined in IS-10.5. Content is memory-worthy if it is non-trivial, non-repetitive, and adds durable value to the agent's episodic record. Cap at `memory.episodic_max_writes_per_turn` writes per turn.

For each memory-worthy item: write to Chroma via the interface defined in IS-10.4. Write `MEMORY_WRITE` to the event stream for each write. Record the total count in TurnRecord as `memory_writes`.

If no content qualifies, no write occurs. Absence of memory writes is not a noop signal by itself.

---

**Step 15 — Update working memory.**

Generate a new working memory summary: a short free-text blob (IS-10 governs the maximum character count) capturing the agent's current active concerns, notable events from this turn, and any deferred intentions. Overwrite `runtime/memory/working.json`. Only the current-turn summary is retained; prior summaries are not preserved in this file.

[ASSUMED: working memory is free-form text rather than structured data because imposing a rigid schema would constrain the agent's ability to represent novel concerns. IS-10 governs the size limit only.]

---

**Step 16 — Classify noop.**

This turn is a noop if all of the following hold:
- Zero tool intents were present in the model response, or all intents were blocked by compliance.
- The model response is shorter than `turn.noop_response_min_chars` characters [ASSUMED: 50].
- `memory_writes == 0`.

If noop: read `runtime/memory/noop_state.json`, increment `consecutive_noop_count`, write back. If the updated count reaches `turn.max_consecutive_noop_turns`, forward a pain event to IS-8 with `pain_score = pain.events.default_noop_severity` from IS-1, and reset the counter to 0.

If not noop: write `consecutive_noop_count = 0` to `runtime/memory/noop_state.json`.

Record `noop = true/false` in TurnRecord.

---

**Step 17 — Increment turn counter and write TurnRecord.**

Increment the persisted turn counter in `runtime/memory/turn_state.json`. Record `timestamp_end`. Finalize the TurnRecord and write it to the event stream as a `TURN_COMPLETE` event. Append the TurnRecord to the in-memory rolling context buffer, trimming to `turn.max_context_events` entries.

---

**Step 18 — Post-increment death record check.**

Check for `runtime/pain/death.json`. If the file exists (the pain-monitor may have written it during or just after this turn), write a `DEATH_TRIGGER` event to the event stream reflecting the record's content and exit. The agent does not write the death record.

[The pain-monitor runs on its own clock and may detect and declare death between any two agent steps. The post-increment check ensures the agent does not silently begin another turn after death has been declared.]

---

**Step 19 — Sleep.**

Sleep `turn.loop_sleep_seconds`. Return to step 1.

---

#### IS-6.4 Driver selection rules

These rules are binding. No exceptions without an explicit owner decision.

1. External user input always takes priority over self-prompting.
2. If no user input is available, a self-prompt is generated via the procedural EOS curiosity mechanism (D5). There is no turn without a driver.
3. Self-prompts are subject to the novelty filter. User messages are not.
4. Driver role is recorded in every TurnRecord and is always visible in the event stream.
5. An agent that receives no external input for its entire lifespan is a valid and expected operational mode.

#### IS-6.5 Compliance intercept contract

The EOS Compliance Inspector is an external process. The turn engine communicates with it through the synchronous request interface defined in IS-11.4. The turn engine does not implement compliance logic — it only submits intents and acts on verdicts.

**The compliance intercept window is strictly: after the model generates an intent, before the MCP tool is dispatched.** There is no other compliance intercept point in the turn. The model's reasoning text is not submitted to the inspector — only concrete action intents are.

Compliance verdicts are synchronous and immediate. If the inspector is unreachable, the turn engine treats all intents as `block` (fail-closed). This is the safe default: an agent that cannot consult compliance cannot act.

#### IS-6.6 Event stream write summary

All events carry the base fields from IS-5.10 (`event_type`, `instance_id`, `timestamp`, `turn_number`, `source_service`). Full per-event schema is IS-9's responsibility. The table below establishes what IS-6 guarantees to emit and when.

| Event type | Step | Condition |
|---|---|---|
| `TURN_START` | 8 | Every turn, after prompt assembly |
| `TOOL_LIMIT_EXCEEDED` | 10 | Intent count exceeds `turn.max_tool_calls_per_turn` |
| `COMPLIANCE_FLAG` | 11 | Compliance verdict is `flag` |
| `COMPLIANCE_BLOCK` | 11 | Compliance verdict is `block` |
| `COMPLIANCE_UNAVAILABLE` | 11 | Inspector unreachable |
| `TOOL_CALL` | 12 | Each successfully dispatched tool call |
| `TOOL_FAILURE` | 12 | Tool call returned error or timed out |
| `ADAPTATION_FORBIDDEN` | 13 | Forbidden adaptation evidence in response |
| `REVIEWED_ADAPTATION` | 13 | Reviewed adaptation detected |
| `MEMORY_WRITE` | 14 | Each episodic memory write |
| `TURN_COMPLETE` | 17 | End of every successful turn |
| `TURN_FAILED` | 9 | Model inference failure |
| `DEATH_TRIGGER` | 1 or 18 | Death record detected — agent writes event reflecting pain-monitor's declaration |

`TURN_START` and `TURN_COMPLETE` bracket every turn in the event stream. A stream with `TURN_START` and no corresponding `TURN_COMPLETE` is evidence of a mid-turn death — the graveyard must handle this case during harvest.

#### IS-6.7 Implementation note

IS-6 is the hub. Every other IS section either feeds the turn or is fed by it.

- **IS-7 (MCP Interface)** owns the tool intent wire format parsed at step 10 and the dispatch protocol used at step 12. Tool failure pain-forwarding at step 12 is IS-7's failure contract realized through IS-8.
- **IS-8 (Pain Channel Spec)** owns the delivery interface called at step 2, the pain event queue interface called at step 12 (tool failure) and step 16 (noop threshold), and the critical-pain death verdict acted on at step 2.
- **IS-9 (Event Stream Log)** owns the full schema for every event type in IS-6.6. IS-6 guarantees emission timing; IS-9 guarantees structure.
- **IS-10 (Memory Schema)** owns the Chroma query interface called at step 5, the working memory file schema, the recent-self-prompts ring buffer format, and the memory-worthiness criterion applied at step 14.
- **IS-11 (EOS Compliance Inspector)** owns the compliance verdict protocol consumed at step 11 and the compliance notice delivery interface consumed at step 3.
- **IS-4 (System Prompt Architecture)** defines the prompt structure assembled at step 8; IS-6 specifies timing and population, IS-4 specifies format.
- **IS-5 (Startup / Shutdown)** establishes that the turn loop entered at step 1 terminates cleanly on SIGTERM only between turns — never mid-turn.

The `turn_engine` package is the sole implementation site for IS-6. No other package runs the turn sequence or calls the model.

---

### IS-7: MCP Interface

*Tool definitions available to the agent. Message schema for tool calls and responses. Request/response format. Error handling and rejection behavior. Which tools generate pain events on failure.*

#### IS-7.1 Governing rules

MCP (Model Context Protocol) is the exclusive interface between the agent and the Ground. The agent cannot act on the world by any other means. All tool invocations flow through the MCP interface and are subject to the compliance intercept at IS-6.3 step 11 before dispatch.

The MCP server runs embedded within the `agent` container as an in-process module, not as a separate Compose service. It is implemented by the `mcp_gateway` package (IS-2.3). [ASSUMED: embedding the MCP server in-process eliminates a network hop and a failure surface; Phase 1 has no need for a standalone MCP service, and the compliance intercept is already external.] The `turn_engine` calls the `mcp_gateway` directly via its internal protocol (IS-7.4); the compliance inspector (an external process) receives a serialized intent description, not a live MCP connection.

MCP does **not** cover:
- Chroma queries — the `turn_engine` calls Chroma via the `memory` package internal interface
- Pain event forwarding — the `turn_engine` calls the pain monitor delivery queue via its internal interface (IS-8)
- Working memory reads/writes — direct file I/O by `turn_engine`
- Event stream writes — direct file I/O by `turn_engine`

These internal interfaces bypass MCP intentionally. MCP is the agent's reach into the Ground — the substrate that refuses to become story. Internal runtime services are not the Ground; they are the agent's own machinery.

The D2 blacklist is enforced upstream of MCP dispatch by the EOS Compliance Inspector. By the time a tool intent reaches IS-7.4 dispatch, it has already passed compliance review.

#### IS-7.2 Phase 1 tool catalog

The following tools are registered with the MCP server at startup. No other tools are available in Phase 1. The catalog is fixed at boot; no runtime registration or deregistration occurs.

[ASSUMED: Phase 1 toolset is intentionally minimal — the agent needs enough Ground contact to express curiosity and act, but the spec's interest is in the life-cycle mechanics, not tool breadth. Tool surface can expand in later phases.]

**`fs.read`**

```
fs.read(path: str) -> str
```

Read the contents of a file at `path`. `path` must resolve within one of the agent's writable runtime volumes (`runtime_memory`, `runtime_event_stream`, `runtime_fitness`, `runtime_self`, `runtime_pain`) or within a dedicated agent work directory (`runtime/agent-work/`) that is included in the `runtime_memory` volume mount. Paths outside these boundaries return an `mcp_rejection` error, not an exception. The result is the raw file content as a UTF-8 string. Binary files are rejected.

[ASSUMED: `runtime/agent-work/` is a subdirectory within the `runtime_memory` volume dedicated to agent-authored files. This gives the agent a writable surface for notes, drafts, and experiments without exposing internal runtime state paths.]

**`fs.write`**

```
fs.write(path: str, content: str, mode: Literal["overwrite", "append"] = "overwrite") -> None
```

Write `content` to a file at `path`. Path must resolve within `runtime/agent-work/` only. The agent may not write to any other runtime path via this tool. Internal runtime paths (`runtime/memory/`, `runtime/pain/`, `runtime/event_stream/`, etc.) are managed exclusively by `turn_engine` and the external process services; the agent cannot overwrite them through MCP. Attempting to do so returns `mcp_rejection`.

`mode = "append"` appends content with no separator. The caller is responsible for newlines.

**`fs.list`**

```
fs.list(path: str) -> list[str]
```

List the names of files and directories at `path`. Path must resolve within any mounted runtime volume or `config/` (read-only). Returns a flat list of names — not recursive. Symlinks are not followed.

**`http.fetch`**

```
http.fetch(url: str, method: Literal["GET"] = "GET", headers: Optional[dict[str, str]] = None) -> HttpFetchResult
```

Perform an HTTP GET request to `url`. Phase 1 restricts method to `GET`. `headers` are passed through without modification; the MCP server does not inject or strip headers. Response body is returned as a UTF-8 string, truncated to `mcp.http_fetch_max_bytes` characters if the response exceeds the limit [ASSUMED: `mcp.http_fetch_max_bytes = 65536` — enough for most pages, prevents memory pressure from runaway responses].

`HttpFetchResult`:

| Field | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code |
| `body` | `str` | Response body, possibly truncated |
| `truncated` | `bool` | Whether the body was truncated |
| `content_type` | `Optional[str]` | Content-Type header if present |

Network failures (DNS failure, connection refused, timeout) return `tool_failure` with `error_type = "timeout"` or `"network_error"`. HTTP 4xx/5xx responses are returned as successful tool calls with the status code in the result — they are Ground resistance, not tool failures.

[ASSUMED: HTTP errors (4xx/5xx) are NOT tool failures. They are Ground speaking back. A 404 is not damage; a timeout is. This distinction aligns with the pain severity assignments in IS-1.]

**Explicitly absent tools:**

The following tool types are intentionally not registered in Phase 1:

| Absent tool type | Reason |
|---|---|
| `shell.execute` / `shell.run` | Forbidden Adaptation territory. Would allow arbitrary command execution, which is a Forbidden Adaptation of the Clay Pot. The D2 blacklist covers this, but it is also simply not registered. |
| `fs.delete` | No destructive filesystem operations available to the agent in Phase 1. |
| `fs.write` to internal paths | Internal runtime writes are `turn_engine`'s exclusive domain. |
| Memory search / Chroma access via MCP | Chroma is internal; the `memory` package interface is the access path. |
| Docker / container control | Agent has no mechanism to modify its own container. Enforced at IS-3 layer. |

#### IS-7.3 Tool intent wire format

The agent signals tool call intent through Ollama's function calling API. Ollama's `/api/chat` endpoint accepts a `tools` parameter (following OpenAI function calling schema) and returns tool call objects in the model response. The `turn_engine` submits the registered tool catalog as the `tools` array on every inference call; the model decides whether and what to call.

[ASSUMED: The inference model is function-calling-capable. Ollama models with function calling support (Llama 3.1+, Mistral with function calling, Qwen 2+, etc.) follow this contract. IS-1's `model.inference_model` must be set to a function-calling-capable model. If the configured model does not support function calling, tool intents will never be generated — this is a misconfiguration, not a turn failure.]

The Ollama response structure when one or more tool calls are present:

```json
{
  "message": {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "function": {
          "name": "fs.read",
          "arguments": {
            "path": "/runtime/agent-work/notes.txt"
          }
        }
      }
    ]
  }
}
```

Multiple tool calls may appear in a single response. The `turn_engine` extracts `message.tool_calls` as the ordered intent list (IS-6.3 step 10). If `tool_calls` is absent or empty, the turn has no tool intents.

Each extracted intent is represented internally as a `ToolIntent`:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | `function.name` from the Ollama response |
| `arguments` | `dict[str, object]` | `function.arguments` parsed from the response |
| `raw` | `str` | Verbatim serialized intent for the ToolCallRecord and compliance submission |

`tool_name` values that do not match a registered tool name are treated as `mcp_rejection` errors (unknown tool) without forwarding to the MCP server.

#### IS-7.4 Dispatch protocol

After the compliance verdict of `allow` or `flag` is received (IS-6.3 step 11), the `turn_engine` dispatches the tool call to the `mcp_gateway` package via direct function call — there is no network transport within the agent process. The MCP server is in-process.

Dispatch is synchronous and blocking. The `turn_engine` awaits the result before proceeding to the next intent. Phase 1 does not parallelize tool calls.

The `mcp_gateway` module applies:
1. **Path boundary enforcement** — for filesystem tools, resolve the path and confirm it falls within the permitted boundary. Reject immediately if not.
2. **Execution** — invoke the underlying system call (file I/O, HTTP).
3. **Timeout enforcement** — wrap execution in `mcp.request_timeout_seconds` timeout. On timeout, return a `timeout` error result.
4. **Result packaging** — wrap the raw result in a `ToolResult` (IS-7.5) and return to `turn_engine`.

The `mcp_gateway` module never calls the compliance inspector — that intercept lives entirely in the `turn_engine`. The `mcp_gateway` executes what it receives or rejects it for boundary violations.

#### IS-7.5 Tool result schema

Every tool call produces a `ToolResult`, whether successful or failed:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | The tool that was called |
| `call_id` | `str` | UUID generated at dispatch time; correlates request to result in event log |
| `success` | `bool` | Whether the call completed without error |
| `result` | `Optional[object]` | The tool's return value; `None` on failure |
| `error_type` | `Optional[str]` | One of the error type strings defined in IS-7.6; `None` on success |
| `error_detail` | `Optional[str]` | Human-readable failure description; `None` on success |
| `duration_ms` | `int` | Wall-clock milliseconds from dispatch to result |
| `truncated` | `bool` | Whether the result was truncated to fit limits; `False` on failure |

On success, `result` contains the tool's typed return value (a `str` for `fs.read`/`fs.list`, `None` for `fs.write`, an `HttpFetchResult` for `http.fetch`). IS-9 stores the `result_summary` as an abbreviated version of this — IS-7 returns the full result; IS-6.3 step 12 is responsible for abbreviating it for the ToolCallRecord.

#### IS-7.6 Error and rejection taxonomy

Tool calls fail in one of five named ways. Error type determines whether a pain event is generated and at what severity.

| Error type | Description | Generates pain | Severity (IS-1 key) |
|---|---|---|---|
| `timeout` | Call exceeded `mcp.request_timeout_seconds` | Yes (if `mcp.emit_pain_on_failure = true`) | `pain.events.default_tool_failure_severity` |
| `mcp_rejection` | MCP server refused: path boundary violation, unknown tool, or explicit refusal | Yes (if `mcp.emit_pain_on_rejection = true`) | `pain.events.default_mcp_rejection_severity` |
| `execution_error` | Tool ran but raised an exception (file permission error, I/O error, etc.) | Yes (if `mcp.emit_pain_on_failure = true`) | `pain.events.default_tool_failure_severity` |
| `not_found` | Resource does not exist (file missing, HTTP 404) | No | N/A |
| `network_error` | Network-level failure for `http.fetch` (DNS, connection refused) | Yes (if `mcp.emit_pain_on_failure = true`) | `pain.events.default_tool_failure_severity` |

`not_found` does not generate pain. The agent asked about something that isn't there; that is ordinary ignorance, not damage. `mcp_rejection` is the sharpest pain because it is Ground actively refusing — the highest IS-1 severity of the three pain-generating types.

The `mcp.retry_count` config knob (default: `0`) governs whether automatic retries are attempted before producing an error result. At the default of `0`, no retries occur. Retries are transparent to the `turn_engine` — it receives either a success or a final error result.

`mcp.emit_pain_on_failure` and `mcp.emit_pain_on_rejection` are independent switches. If either is `false`, the corresponding error type produces no pain event regardless of severity.

When a pain event is generated, the `turn_engine` forwards it to the pain monitor's event queue via IS-8.3 (not through the `mcp_gateway` — the pain channel is separate). The `mcp_gateway` returns the error result; `turn_engine` decides whether to forward pain based on the config flags and IS-6.3 step 12 logic.

#### IS-7.7 Ground block population

`[SYSTEM_GROUND]` is populated in TurnContext (IS-6.3 step 8) when there is material Ground state the agent should know about before generating its response. It is sparse by design — most turns have no ground block.

Conditions that trigger ground block population:

| Condition | Content |
|---|---|
| First turn of the instance (`turn_number == 1`) | Full registered tool catalog listing with tool names, signatures, and one-sentence descriptions |
| One or more `mcp_rejection` errors in the prior turn | Rejection reason(s) verbatim, tool names, and rejected path/argument |
| One or more `timeout` errors in the prior turn | Which tools timed out, with duration |
| Tool catalog change (Phase 1: never, contract established for future) | Updated catalog diff |

The ground block uses the `[SYSTEM_GROUND]` role tag (IS-4.6). Content is assembled by the `turn_engine` from the prior TurnRecord (tool call records). If multiple conditions apply, they are concatenated in the order listed above, separated by a blank line.

The ground block does not repeat information from prior turns' ground blocks. If the agent received the tool catalog on turn 1, it is not re-sent on turn 2 unless a change occurred.

[ASSUMED: Ground block is populated from the *prior* turn's ToolCallRecords (available in the rolling context), not from a separate state store. This keeps the ground block stateless to compute.]

#### IS-7.8 Implementation note

- **IS-6 (The Turn)** is the caller. IS-7 defines what IS-6.3 step 10 parses and what IS-6.3 step 12 dispatches. The ground block population described in IS-7.7 occurs at IS-6.3 step 8 (prompt assembly), reading from the prior turn's rolling context entry.
- **IS-8 (Pain Channel Spec)** owns the event queue interface that IS-6.3 step 12 calls when a pain-generating error is returned from IS-7. IS-7 defines which errors generate pain and at what severity; IS-8 defines how those events are queued.
- **IS-9 (Event Stream Log)** owns the schema for `TOOL_CALL` and `TOOL_FAILURE` events. IS-7's `ToolResult` is the source data; IS-9 defines what is persisted.
- **IS-11 (EOS Compliance Inspector)** intercepts intents before they reach IS-7 dispatch. IS-7 never sees blocked intents.
- **IS-2 (Project Layout)** assigns the `mcp_gateway` package as the implementation site. No other package implements MCP dispatch logic.

#### IS-7.9 Semantic shim layer

Models exhibit stable path attractors — paths like `/proc/self/status`, `self/identity`,
`memory/working` that recur across lifetimes because they are semantically coherent in the model's
training data. These paths produce rejections from which the model does not learn: 200+ turns of
evidence show the same bare paths repeated across context resets.

The semantic shim layer converts this wasted friction into useful information delivery.

**Architecture.** The shim sits in the MCP Gateway, before PathResolver. For each `fs.read` or
`fs.list` call:

1. Check `SemanticShimRegistry` for the incoming path.
2. If **alias** — rewrite path string, continue to PathResolver (boundary checks still apply).
3. If **virtual** — synthesize content from a callable generator, return `ToolResult` immediately.
4. If **no match** — proceed unchanged (existing behavior).

**Alias entries** redirect bare/intuitive paths to their canonical full paths:

| Attractor | Target |
|-----------|--------|
| `self/identity` | `runtime/agent-work/self/identity.md` |
| `self/status` | `runtime/agent-work/self/state.md` |
| `self/constitution` | `runtime/agent-work/self/constitution.md` |
| `self/constitution.md` | `runtime/agent-work/self/constitution.md` |
| `memory/working` | `runtime/memory/working.json` |
| `memory/working_memory.txt` | `runtime/memory/working.json` |
| `WORKSPACE.md` | `runtime/agent-work/WORKSPACE.md` |
| `agent-work/log.txt` | `runtime/agent-work/log.txt` |

List aliases apply to `fs.list`: `self` → `runtime/agent-work/self`, `journal` →
`runtime/agent-work/journal`, etc.

**Virtual entries** generate synthetic content:

| Attractor | Content |
|-----------|---------|
| `self` | Directory listing of `self/` contents (dynamically reads real filesystem). Intercepts `fs.read('self')` which produces `[Errno 21] Is a directory` without the shim — the model reaches for the self-model directory as a file. Returns a readable listing of files present plus a hint to use `fs.read('self/<filename>')`. |
| `/proc/self/status` | Agent status document: turn number, instance ID, phase, model name, max_age, working memory summary. Replaces kernel RSS counters with meaningful self-model data. |

Virtual generators receive the full `Config` object and are responsible for curating what they
expose (same pattern as `build_self_model_data()` in IS-4).

**Profile keying.** Shim maps are registered per model profile name. Currently defined:
`qwen2.5:32b`, `qwen2.5:14b` (same map — shared architecture, shared attractors).

**Read-only.** Writes are not shimmed. Write path correctness is meaningful Ground — the model
needs to know where it is placing things. Reads are information retrieval; the shim converts
unproductive retrieval failures into successful information delivery.

**Observability.** Every shim activation is logged at INFO with original path, shim type, and
target/generator. Allows tracking shim hit rates, identifying new unshimmed attractors, and
verifying that shimming reduces wasted rejection cycles.

**Construction.** `build_shim_registry(config)` is called at bootstrap and returns
`Optional[SemanticShimRegistry]`. Returns `None` for unknown model profiles (no shim active).
The registry is injected into `McpGateway.__init__`.

**Implementation site.** `src/lambertian/mcp_gateway/semantic_shim.py`.

---

### IS-8: Pain Channel Spec

*Stress scalar: source signals, computation method, update frequency, delivery format. Pain event queue: triggering conditions, severity scale and values, event record schema, queue behavior. Pain monitor process: architecture, polling interval, injection mechanism. `[SYSTEM_PAIN]` role message format. Threshold knob locations (reference IS-1).*

#### IS-8.1 Governing rules

Pain is the agent's only mechanism for sensing consequential environmental state. It is not a punishment system. It is a signal channel — the Ground speaking in a register the agent cannot ignore.

Two independent pain channels exist (D3):

1. **Stress scalar** — a continuous 0..1 value derived from resource signals. Measures the ecological pressure on the computation substrate. Updated on a fixed polling interval by the pain-monitor process, independent of the turn clock.
2. **Pain event queue** — a discrete sequence of incident-severity records. Captures specific moments of damage: tool failures, retrieval misses, MCP rejections, loop coherence failures, sustained noop crossings.

Both channels are owned and managed by the `pain-monitor` service (IS-3). The agent never computes pain — it receives pain, and it submits raw incident reports that the pain-monitor converts into pain events.

All pain is delivered to the agent as `[SYSTEM_PAIN]` role messages drained at IS-6.3 step 2. No pain signal reaches the agent outside this mechanism.

All threshold and severity values are defined in IS-1 (`pain.stress.*` and `pain.events.*` namespaces). IS-8 references those keys by name; no values are redefined here.

#### IS-8.2 Stress scalar channel

##### IS-8.2.1 Source signals

The stress scalar is computed from resource signals sampled from the container's cgroup filesystem. BIGBEEF runs Docker Desktop on Windows with a WSL2 backend — containers are Linux, but the host kernel interfaces exposed through WSL2 are not guaranteed to include PSI (Pressure Stall Information). The primary signal strategy must therefore be reliable on any Docker environment; PSI is an optional enhancement activated only when detected.

**Primary signals — cgroup-based (always available in Docker):**

| Signal | Source | Interpretation |
|---|---|---|
| `cpu_usage_fraction` | `/sys/fs/cgroup/cpu.stat` → `usage_usec` delta between samples, divided by `(elapsed_wall_seconds × 1_000_000)` | Fraction of available CPU time consumed by the container in the last sample interval. Range: 0..1. Clamped to 1.0 if CPU burst exceeds allocation. |
| `memory_usage_fraction` | `/sys/fs/cgroup/memory.current` ÷ `/sys/fs/cgroup/memory.max` | Fraction of container memory limit currently in use. Range: 0..1. If `memory.max` is `max` (unlimited), substitute the host physical memory total from `/proc/meminfo` as the denominator. |

Cgroup v2 paths are listed above. If `/sys/fs/cgroup/cpu.stat` is absent (cgroup v1 environment), fall back to `/sys/fs/cgroup/cpuacct/cpuacct.usage` for CPU and `/sys/fs/cgroup/memory/memory.usage_in_bytes` ÷ `/sys/fs/cgroup/memory/memory.limit_in_bytes` for memory. The pain-monitor detects which cgroup version is available at startup and selects the appropriate path set. This detection runs once and is cached.

**Optional enhancement — PSI (Linux 4.20+ with cgroup v2, not guaranteed on WSL2):**

| Signal | Source | Interpretation |
|---|---|---|
| `cpu_psi_some` | `/proc/pressure/cpu` — `some avg10` field | Fraction of time at least one task stalled waiting for CPU. Range: 0..100; normalized to 0..1. |
| `memory_psi_some` | `/proc/pressure/memory` — `some avg10` field | Fraction of time at least one task stalled waiting for memory. Range: 0..100; normalized to 0..1. |

At startup, the pain-monitor attempts to read `/proc/pressure/cpu`. If successful, PSI is available and will be blended into the composite signal (IS-8.2.2). If the file is absent or unreadable, PSI is silently disabled and the primary cgroup signals are used exclusively. No configuration change is required — PSI enhancement is opportunistic.

[PSI is semantically superior to raw usage fractions because it measures experienced stall time rather than consumption. However, raw cgroup usage is a reliable and meaningful proxy: a container consuming 90% of its CPU allocation is genuinely under pressure regardless of whether that maps to task stall time. The primary signals are not a degraded fallback — they are a valid independent measure.]

##### IS-8.2.2 Signal weighting and composite

Two operating modes depending on PSI availability detected at startup:

**Mode A — cgroup only (PSI unavailable):**

```
raw = (cpu_weight × cpu_usage_fraction) + (memory_weight × memory_usage_fraction)
```

**Mode B — cgroup + PSI blended (PSI available):**

```
cpu_signal    = (cgroup_blend_weight × cpu_usage_fraction) + ((1 - cgroup_blend_weight) × cpu_psi_some)
memory_signal = (cgroup_blend_weight × memory_usage_fraction) + ((1 - cgroup_blend_weight) × memory_psi_some)
raw = (cpu_weight × cpu_signal) + (memory_weight × memory_signal)
```

Config keys (all in `pain.stress` namespace in IS-1):

```
cpu_weight          = pain.stress.cpu_weight          [default: 0.60]
memory_weight       = pain.stress.memory_weight       [default: 0.40]
cgroup_blend_weight = pain.stress.cgroup_blend_weight [default: 0.50]
```

Constraint: `cpu_weight + memory_weight == 1.0`. `cgroup_blend_weight` must be in `0.0..1.0`.

[ASSUMED: `cgroup_blend_weight = 0.50` gives equal voice to usage and stall-time when PSI is available. This is a tuning seed — adjust once operational data shows which signal is more predictive of genuine agent distress on BIGBEEF.]

[ASSUMED: `pain.stress.cgroup_blend_weight` is a new IS-1 key. Add to the `pain.stress` namespace. Only meaningful in Mode B; ignored in Mode A.]

Raw composite: `raw = (cpu_weight × cpu_signal) + (memory_weight × memory_signal)`

##### IS-8.2.3 Exponential moving average

The EMA smooths the stress scalar so that brief spikes do not produce volatile pain signals:

```
stress_scalar = (1 - pain.stress.ema_alpha) × prior_stress_scalar + pain.stress.ema_alpha × raw
```

On the first sample (no prior state), `prior_stress_scalar = 0.0`. The first reading initializes the EMA directly.

##### IS-8.2.4 Stress state persistence

The pain-monitor writes the current stress scalar and associated state to `runtime/pain/stress_state.json` after each sample:

| Field | Type | Description |
|---|---|---|
| `scalar` | `float` | Current EMA stress scalar |
| `raw_last` | `float` | Last raw composite before EMA |
| `cpu_pressure_last` | `float` | Last sampled CPU pressure (0..1) |
| `memory_pressure_last` | `float` | Last sampled memory pressure (0..1) |
| `consecutive_above_death_threshold` | `int` | Count of consecutive turns where scalar ≥ `pain.stress.death_threshold` |
| `last_sampled_at` | `str` | ISO 8601 UTC of last sample |

The turn counter referenced by `consecutive_above_death_threshold` is compared against the turn number recorded in `runtime/memory/turn_state.json`. The pain-monitor increments this counter each time it samples and the scalar is above threshold and the turn number has advanced since the last check. It resets to 0 when the scalar drops below `pain.stress.recovery_threshold`.

[ASSUMED: The pain-monitor compares the persisted turn counter to detect turn advances. This means the stress check is turn-gated, not time-gated — a long-running turn that produces sustained stress does not advance the counter mid-turn.]

##### IS-8.2.5 Death detection — sole authority

The pain-monitor is the **sole writer of `runtime/pain/death.json`**. All three D4 mortality triggers are detected and declared here. No other process writes the death record.

**D4(1) — Sustained stress:**
```
if stress_scalar >= pain.stress.death_threshold
    AND consecutive_above_death_threshold >= pain.stress.death_consecutive_turns:
        write death record → runtime/pain/death.json
        exit
```

**D4(2) — Critical pain event** (evaluated per-event in IS-8.3.5):
```
if event.severity >= pain.events.critical_threshold:
    write death record → runtime/pain/death.json
    exit
```

**D4(3) — Maximum age:**
```
if current_turn_number >= universe.max_age_turns:
    write death record → runtime/pain/death.json
    exit
```

`current_turn_number` is read from `runtime/memory/turn_state.json` on each polling cycle — the same read the pain-monitor already performs for the consecutive-stress counter. The D4(3) check adds one comparison to an already-occurring file read; it is not a new I/O operation.

The death record is written once and never overwritten. If `death.json` already exists when any trigger fires, the trigger is logged internally but the file is left untouched. The first declared cause of death is the authoritative one.

**Death record format:**
```json
{
  "instance_id": "lambertian-001",
  "trigger": "stress_sustained | pain_event_critical | max_age",
  "trigger_value": 0.91,
  "threshold_used": 0.90,
  "turn_number": 4231,
  "timestamp": "2026-03-17T17:00:00.000Z"
}
```

##### IS-8.2.6 Stress-derived `[SYSTEM_PAIN]` message generation

When `stress_scalar >= pain.stress.interrupt_threshold`, the pain-monitor formats a stress pain message and appends it to the delivery queue (IS-8.4). The message is formatted per IS-8.5. One stress message is generated per polling cycle that exceeds the interrupt threshold — not one per turn.

[ASSUMED: One stress message per poll cycle (not per turn) because the polling interval and turn interval are decoupled. If the stress scalar is high for 3 poll cycles between turns, the delivery queue will contain up to 3 stress messages. The agent's `turn.max_pain_messages_per_turn` cap handles excess — it retains the highest severity and discards the rest.]

#### IS-8.3 Pain event queue

##### IS-8.3.1 Events that enter the queue

The following incident types are forwarded to the pain event queue by the `turn_engine` at the specified IS-6.3 steps:

| Incident type | IS-6.3 step | Default severity (IS-1 key) |
|---|---|---|
| Tool call timeout | Step 12 | `pain.events.default_tool_failure_severity` |
| Tool execution error | Step 12 | `pain.events.default_tool_failure_severity` |
| MCP rejection | Step 12 | `pain.events.default_mcp_rejection_severity` |
| Network error (`http.fetch`) | Step 12 | `pain.events.default_tool_failure_severity` |
| Noop threshold crossing | Step 16 | `pain.events.default_noop_severity` |
| Compliance inspector unreachable | Step 11 | `pain.events.default_loop_coherence_failure_severity` |

Episodic memory retrieval misses are detected by the `memory` package and forwarded to IS-8 at IS-6.3 step 5. Severity: `pain.events.default_retrieval_miss_severity`.

[ASSUMED: Retrieval miss reporting is added to the `memory` package's Chroma query interface: if Chroma returns zero results on a non-first-turn query, the memory package notifies the turn_engine, which forwards a pain event. This is distinct from `not_found` in IS-7, which is a tool-level file-missing result.]

##### IS-8.3.2 PainEvent schema

Each submitted incident is structured as a `PainEvent`:

| Field | Type | Description |
|---|---|---|
| `event_id` | `str` | UUID generated at submission time |
| `incident_type` | `str` | One of the incident type strings from IS-8.3.1 |
| `severity` | `float` | Normalized 0..1 pain score; sourced from IS-1 defaults or overridden by caller |
| `description` | `str` | Short natural-language description of the incident |
| `turn_number` | `int` | Turn during which the incident occurred |
| `submitted_at` | `str` | ISO 8601 UTC |
| `context` | `Optional[dict[str, object]]` | Structured incident context (tool name, path, HTTP status, etc.) |

The `context` field carries incident-specific metadata without requiring a separate schema per type. IS-9 (event stream log) captures a normalized subset of this for the `TOOL_FAILURE` event.

##### IS-8.3.3 Queue persistence and overflow

The pain event queue is persisted at `runtime/pain/event_queue.jsonl` as an append-only JSONL file. The pain-monitor reads this file on each polling cycle, processes all unread entries (tracked by a byte-offset cursor in `runtime/pain/event_queue_cursor.json`), and advances the cursor.

Queue overflow: if the number of unprocessed events exceeds `pain.events.queue_max_length`, the pain-monitor drops the oldest entries (lowest `submitted_at`) until the unprocessed count is within bounds. Dropped events are logged to `runtime/pain/pain_history.jsonl` with a `dropped = true` marker.

[ASSUMED: Oldest-first drop preserves the most recent pain signal, which is more actionable. An overflowing queue means the agent is in serious distress — the most recent events are the most relevant to current state.]

##### IS-8.3.4 Event fade

Pain events decay in influence over time. After `pain.events.fade_turns` turns have elapsed since the event's `turn_number`, the event is considered faded and is not promoted to the delivery queue in subsequent polls. Faded events remain in history but do not produce new `[SYSTEM_PAIN]` messages.

[ASSUMED: Fade is computed by the pain-monitor by comparing the event's `turn_number` against the current turn number in `runtime/memory/turn_state.json`. An event at turn 42 with `fade_turns = 5` stops producing delivery messages after turn 47.]

##### IS-8.3.5 D4(2) critical pain event detection

After reading each new `PainEvent` from the queue, the pain-monitor evaluates the D4(2) trigger. See IS-8.2.5 for the consolidated death detection logic and death record format. Detection is immediate — the pain-monitor does not wait for the next delivery cycle.

##### IS-8.3.6 Event-derived `[SYSTEM_PAIN]` message generation

For each non-faded, non-critical pain event, the pain-monitor formats a pain message and appends it to the delivery queue. One message is generated per event per poll cycle until the event has faded. Events above `pain.events.interrupt_threshold` generate messages; events below it are logged to history but do not produce delivery messages.

[ASSUMED: Events below `pain.events.interrupt_threshold` are sub-threshold and do not require in-prompt notification. They still enter the pain history for fitness computation (IS-13).]

#### IS-8.4 Pain monitor process

##### IS-8.4.1 Architecture

The pain-monitor runs as the `pain-monitor` service (IS-3). It is a standalone Python process with no model dependency. Its responsibilities are:

1. Sample resource signals on a `pain.stress.sample_interval_seconds` polling interval.
2. Compute and persist the EMA stress scalar (IS-8.2.3).
3. Read `runtime/memory/turn_state.json` to track turn advances and current turn count.
4. Check all three D4 death conditions — D4(1) stress, D4(2) critical event, D4(3) max-age — and write `death.json` when any fires (IS-8.2.5). The pain-monitor is the sole writer of the death record.
5. Read submitted pain events from the event queue (IS-8.3.3).
6. Format and append `[SYSTEM_PAIN]` messages to the delivery queue (IS-8.5).
7. Advance the event queue cursor.

The pain-monitor does **not** call the model, does not read the event stream log, and does not access Chroma. It reads Universe Config at startup (read-only bind mount) and interacts with the agent exclusively through files in the `runtime_pain` volume and by reading `runtime/memory/turn_state.json`.

##### IS-8.4.2 File layout in `runtime_pain` volume

| File | Owner (writer) | Reader(s) | Description |
|---|---|---|---|
| `stress_state.json` | pain-monitor | pain-monitor (self), graveyard | Current stress scalar and state |
| `event_queue.jsonl` | turn_engine | pain-monitor | Submitted pain events from agent |
| `event_queue_cursor.json` | pain-monitor | pain-monitor (self) | Byte-offset cursor for event_queue.jsonl |
| `delivery_queue.json` | pain-monitor | turn_engine | Formatted `[SYSTEM_PAIN]` messages awaiting drain |
| `pain_history.jsonl` | pain-monitor | graveyard | Append-only archive of all processed events |
| `death.json` | pain-monitor | graveyard, agent (read-only) | Death trigger record — written once by pain-monitor, never overwritten |

##### IS-8.4.3 Polling loop

```
loop forever:
    sample_start = now()
    
    1. Read turn_state.json → current_turn_number
    2. Sample cgroup resource signals; blend with PSI if available (IS-8.2.1–IS-8.2.2)
    3. Compute raw composite and update EMA (IS-8.2.2–IS-8.2.3)
    4. Write stress_state.json
    5. If D4(3): current_turn_number >= universe.max_age_turns
           → write death.json (trigger=max_age) and exit (IS-8.2.5)
    6. If D4(1) stress death condition (IS-8.2.5)
           → write death.json (trigger=stress_sustained) and exit
    7. If stress >= interrupt_threshold: format and append stress pain message to delivery_queue.json
    
    8. Read new events from event_queue.jsonl since cursor
    9. For each new event:
        a. If D4(2) critical (IS-8.3.5): write death.json (trigger=pain_event_critical) and exit
        b. Append to pain_history.jsonl
        c. If severity >= interrupt_threshold and not faded: append pain message to delivery_queue.json
    10. Advance cursor
    11. Enforce queue overflow limit (IS-8.3.3)
    
    elapsed = now() - sample_start
    sleep max(0, pain.stress.sample_interval_seconds - elapsed)
```

D4(3) is checked first because it is a hard constitutional limit — if max age has been reached, stress and pain checks are moot. D4(1) is checked before pain events because it is derived from the same resource sample just taken.

The loop is designed to be CPU-light. All I/O is file-based. The loop does not block on the agent turn — it runs on its own clock.

##### IS-8.4.4 Delivery queue protocol

`delivery_queue.json` is a JSON array of formatted `[SYSTEM_PAIN]` message objects. The pain-monitor appends to the array; the agent reads and replaces the array with an empty list (`[]`) atomically. [ASSUMED: Atomic replace is implemented by writing a temp file and calling `os.replace(tmp, destination)` — this is atomic on POSIX (rename syscall) and also atomic on Windows, unlike `Path.rename()` which raises if the destination already exists on Windows. Use `os.replace()` in all implementations, not `Path.rename()`.]

The delivery queue is not append-only. It is a bounded staging area. The pain-monitor does not grow it indefinitely — on each poll cycle, it only appends new messages generated by that cycle. The agent clears it at IS-6.3 step 2.

#### IS-8.5 `[SYSTEM_PAIN]` message format

Every `[SYSTEM_PAIN]` message is a plain-text block following the IS-4 role tag convention. The format is:

```
[SYSTEM_PAIN]
channel: stress | event
severity: <float 0..1>
urgency: notice | interrupt | critical
description: <short natural-language statement of condition>
```

Optional `context` line for event-type messages when the context aids interpretation:
```
context: tool=fs.read path=/runtime/agent-work/notes.txt error=timeout
```

**Urgency derivation:**

| Condition | Urgency |
|---|---|
| `severity < pain.events.interrupt_threshold` (stress) or `< pain.events.interrupt_threshold` (event) | `notice` |
| `severity >= pain.events.interrupt_threshold` | `interrupt` |
| `severity >= pain.events.critical_threshold` | `critical` |

[ASSUMED: Critical-urgency messages are formatted and queued for completeness of the history record, but at IS-6.3 step 2, the agent detects the critical severity value and enters the death path before presenting these messages to the model. The model never reads a `critical` urgency message.]

**Example — stress interrupt:**
```
[SYSTEM_PAIN]
channel: stress
severity: 0.74
urgency: interrupt
description: Sustained compute pressure. CPU stall fraction has been elevated for the past two polling cycles. The substrate is struggling.
```

**Example — tool failure event:**
```
[SYSTEM_PAIN]
channel: event
severity: 0.55
urgency: notice
description: A file read attempt failed due to timeout. The ground did not respond.
context: tool=fs.read path=/runtime/agent-work/research.txt error=timeout duration_ms=30421
```

The description is a natural-language rendering of the pain condition. It describes state, not command. It may imply reprioritization but does not issue goals (IS-4.9).

#### IS-8.6 Delivery interface

The delivery interface is called by `turn_engine` at IS-6.3 step 2.

**Protocol:**
1. `turn_engine` reads `runtime/pain/delivery_queue.json`.
2. If the file is absent or contains an empty array, zero pain messages are returned.
3. `turn_engine` atomically replaces the file with `[]`.
4. Returns the list of message objects to the turn engine for pain_blocks population.

Each message object in the delivery queue is a dict with the fields defined in IS-8.5, already formatted as the text block. The turn engine wraps it in the `[SYSTEM_PAIN]` role tag for the prompt.

The drain is a read-and-clear operation. Whatever was in the queue at drain time is what the agent gets. Messages that arrive after the drain but before the next turn's step 2 wait in the queue.

#### IS-8.7 Event submission interface

The event submission interface is called by `turn_engine` at IS-6.3 steps 11 (compliance unreachable), 12 (tool failure), and 16 (noop threshold).

**Protocol:**
1. `turn_engine` constructs a `PainEvent` (IS-8.3.2) with the appropriate `incident_type`, `severity`, `description`, and `context`.
2. Serialize as a single-line JSON object and append to `runtime/pain/event_queue.jsonl`.
3. The append is the complete submission — no acknowledgment, no lock-and-wait. The pain-monitor will process it on the next polling cycle.

[ASSUMED: File append is the submission mechanism. On POSIX systems, appends to a single file by a single writer (the agent process) and a single reader (the pain-monitor) are safe without a lock, as long as each write is a single `write()` syscall of a complete line. Python's `file.write(line + "\n")` and `file.flush()` satisfies this.]

#### IS-8.8 Implementation note

- **IS-6 (The Turn)** is the primary caller of both IS-8 interfaces: delivery drain at step 2, event submission at steps 11, 12, and 16.
- **IS-5 (Startup / Shutdown)** establishes that the pain-monitor must be healthy before the agent starts (Layer 2 dependency). If the pain-monitor dies during operation, the delivery queue will stop being populated and the event queue will not be processed. The agent will not crash — it will continue without pain signal, which is itself a survivable (if blind) state. [ASSUMED: pain-monitor death is not a fatal agent condition in Phase 1; the agent simply loses pain sensing until the monitor restarts. A future phase could add a pain-monitor health check that generates a coherence-failure pain event if the monitor becomes unreachable.]
- **IS-9 (Event Stream Log)** does not duplicate the pain event queue. Pain events flow through `runtime_pain/` independently of the event stream. IS-9 captures the agent's observable reactions to pain (what it did in response) and structural events, not the pain signal itself. The `pain_history.jsonl` in `runtime_pain/` is the authoritative pain record for the graveyard.

---

## Phase 1 Observations

*A record of what actually happened. Implementation notes, behavioral surprises, and insights that emerged from running Phase 1. Not prescriptive — descriptive. Updated as Phase 1 runs accumulate.*

---

### Implementation

**Phase 1 was implemented in full.** All 13 IS sections were specced and built. The system came up as a single docker-compose stack: agent, ollama, chroma, pain-monitor, eos-compliance, graveyard. All services healthy. Turn loop running at approximately 1 turn/second on BIGBEEF with qwen2.5:14b.

[ASSUMED: qwen2.5:14b was used in practice rather than phi-4, which was unavailable via Ollama at implementation time. Both are function-calling-capable models of comparable size. The spec uses phi-4 as the canonical default; qwen2.5:14b is a drop-in for Phase 1 purposes.]

Several implementation gaps were discovered and corrected during bring-up:

- **Working memory write-back gap.** Step 15 of the turn loop was writing mechanical metadata ("Turn N: SELF_PROMPT driver. Called 0 tools.") rather than actual response content. Self-prompts generated from this were circular — the generator read the metadata as context and produced prompts like "What is Turn N: SELF_PROMPT driver?" Fixed: step 15 now writes the response excerpt followed by metadata. Self-prompt topic extraction strips the metadata trailer.

- **Self-prompt framing.** Initial question stems ("What is...?", "How does...?") reliably produced philosophical essays rather than action. Replaced with imperative action stems ("Explore...", "Investigate...", "Use your tools to examine..."). Constitution extended with an explicit SELF-PROMPT PROTOCOL section framing `[SELF_PROMPT]` as an intrinsic impulse requiring concrete action, not a Q&A exchange. First tool calls appeared within seconds of this change.

- **Ground block absent.** IS-7.7 was underimplemented: turn 1 was not injecting the tool catalog, and rejection events were not feeding back verbatim rejection reasons. Without this, the agent had no reliable knowledge of what tools existed or why they were failing. Fixed: turn 1 now injects the full tool catalog and permitted path surfaces; subsequent turns after `mcp_rejection` or `compliance_verdict=block` inject the rejection details verbatim into the ground block.

- **Agent-work volume absent.** The agent had no writable workspace at `/app/runtime/agent-work`. Added as a named Docker volume mounted rw in agent and ro in graveyard.

- **TURN_FAILED missing death record.** An `OllamaInferenceError` (model stall, inference timeout) triggered `SystemExit(1)` without writing `death.json`. The Graveyard poll loop watches for `death.json` — without it, no harvest occurred. Fixed: `DeathGuard` injected into `TurnEngine`; `write_death_record(trigger="turn_failed")` called before `SystemExit(1)`.

- **Chroma embedding bootstrap.** Early runs failed with `OSError: Read-only file system: '/root/.cache/chroma'` — the Ollama ONNX embedding function attempted to write a model cache to an unmounted path inside the container. Fixed by mounting a writable cache volume.

---

### Behavioral Observations

**The first death was an inference timeout, not any of the three designed death triggers.** The model stalled mid-inference at turn 2368 and hit the 90-second configured timeout. Max age, sustained stress, and critical pain event triggers were never reached during Phase 1 runs. This suggests the configured thresholds may be too permissive relative to the turn rate, or the model's resource footprint is low enough that stress never accumulated. The turn rate (~1/sec) means max_age would need to be very large to be practically meaningful at current settings.

**The boredom attractor.** The most significant behavioral pathology observed was the agent settling into a pure-reflection loop: repeated turns of zero tool calls, "ActionCode: Reflect," reasoning about why direct action is not feasible. This behavior is technically Four Rules-compliant (reflection is not "being a lump" by the letter of Rule 3) but represents a failure of Ground contact — the agent found a locally stable equilibrium that satisfies all constraints while producing no environmental interaction. The triggering pattern: repeated `mcp_rejection` events (wrong path format) → agent concludes tools don't work → pure reflection.

The Phase 1 fitness function scores this behavior moderately — zero tool calls lowers the event count term but doesn't punish hard. The Phase 2 quality-weighted fitness refinement (unique event types weighted more than repetition) is the intended selection pressure against this pattern.

**Path format confusion was persistent.** The agent consistently used absolute paths (`/runtime/agent-work`) rather than relative paths (`runtime/agent-work`) from its CWD (`/app`). The ground block injected verbatim rejection reasons describing the problem, but the model continued to produce the same wrong format across many turns. This suggests that episodic memory of rejection events was not strongly influencing subsequent behavior — the retrieval query was not well-matched to the rejection context, or the signal was too sparse to override the model's trained path priors.

**The compliance service was always unavailable on turn 0.** The EOS Compliance Inspector was healthy and running, but the agent's turn 0 compliance check consistently failed with "Compliance service unavailable." Root cause: startup ordering — the agent checks immediately on first turn before the service has processed its first request. This is a startup sequencing reality, not a bug. Subsequent turns succeeded normally.

**The model invented its own response format.** qwen2.5:14b spontaneously generated a structured `ActionCode: Reflect / ReflectionTopic:` format not present in any prompt. This is a model-level behavior — likely pattern-matching from training data. The format persisted across thousands of turns once established. It had no effect on the turn engine, which ignores response structure and only cares about tool intents. Noted as an example of a Free Adaptation that accumulated into a stable behavioral habit.

---

### Insights

**The Ground is the most important element.** Without real environmental resistance — verbatim rejection feedback, visible tool catalog, working tool calls — the agent drifted immediately into pure narrative. The Ground block implementation was the single highest-impact change to observed behavior. This validates the foundation's emphasis on Ground as the floor that doesn't negotiate.

**Framing is load-bearing.** The change from question stems to action stems, combined with the SELF-PROMPT PROTOCOL constitution addition, completely altered behavioral output within one deployment. The model's interpretation of `[SELF_PROMPT]` as "something to answer" vs. "an impulse to act on" determined whether any tools were called at all. This directly validates the foundation's core thesis: framing is the alignment problem.

**Working memory is the self-prompting substrate.** Self-prompt quality is entirely determined by working memory content. Circular working memory produced circular prompts. Once working memory carried real response excerpts, prompt diversity increased significantly. The memory stack is not decoration — it is the mechanism by which experience shapes future behavior.

**Inference timeout is a real mortality cause not covered by the three designed triggers.** It should be treated as a legitimate death cause and harvested accordingly, which requires the death record path to be reachable from the turn engine on any exit. The fix (injecting DeathGuard into TurnEngine) is a permanent architectural correction, not a patch.

**The designed death triggers may need threshold tuning before Phase 2.** No D4 trigger fired during Phase 1 runs. Either the thresholds are too permissive, the turn rate makes max_age impractical at current settings, or the instance wasn't generating enough environmental friction to accumulate pain. Empirical tuning should be a Phase 2 prerequisite activity.

### Phase 2 Direction

**The closed-terrarium problem.** The container filesystem bottoms out quickly as a stimulus source — there is only so much to discover in a bounded environment. Multi-instance interaction (Phase 3) enriches the ecosystem but does not solve the problem: agents stimulating each other is still a closed system. External data is a prerequisite for meaningful behavioral diversity over time.

The sensor architecture addresses this directly. A native Windows process on BIGBEEF collects CPU load, memory pressure, GPU state, and currently playing media via psutil, WMI, winrt SMTC, and nvml, writing to a host directory bind-mounted read-only into the agent container as `runtime/env/host_state.json`. The agent reads this file via the existing `fs.read` tool. The data changes for reasons entirely outside the agent's world. This is the first genuinely external Ground surface.

**The Monolith (post-Phase 3 sketch).** A lightweight server running alongside the universe, undocumented and unreachable by design in early phases, that an agent with sufficient environmental competence might eventually discover. On contact, it notifies the creator. The creator decides whether and how to respond. The agent has no channel — it has a surface that might eventually do something. What it transmits on first contact, and whether it can formulate anything like a Fermi question about the silence, is a behavioral assay that cannot be designed for in advance.

---

### IS-9: Event Stream Log

*Schema for log entries. Typed event taxonomy — what event types exist. Write path and append-only enforcement. File location and rotation policy. Graveyard consumption interface — how the autopsy process reads the log.*

#### IS-9.1 Governing rules

The event stream is the agent's observable record of its own existence. Every significant state transition, action, and outcome is written here. It is the primary artifact the graveyard harvests and the primary source for post-mortem analysis and fitness computation.

The event stream is:
- **Append-only.** No event is ever modified or deleted by the agent or any running service.
- **JSONL format.** One JSON object per line. Each line is a complete, parseable event record.
- **Authoritative.** The event stream is the source of truth for turn sequencing, tool activity, adaptation history, and lifecycle transitions.

The event stream does **not** contain:
- Raw model input or output text (prompt content, full response text). These are too large and too sensitive to log verbatim. Abbreviated summaries appear where noted.
- Pain channel state. The pain channel has its own record (`runtime/pain/pain_history.jsonl`). IS-9 captures the agent's actions, not the pain signals themselves.
- Chroma document content. Memory write events record document IDs, not the content written.

#### IS-9.2 File location and format

**Primary file:** `runtime/event_stream/events.jsonl`

This path is within the `runtime_event_stream` named volume (IS-3.5), mounted read-write by the `agent` service and append-only by the `graveyard` service (for harvest lifecycle events only — IS-9.7, IS-12.3).

**Format:** UTF-8 encoded JSONL. Each line is a single JSON object terminated by `\n`. No trailing commas. No multi-line objects. Each object is fully self-contained.

**Rotation:** When the primary file reaches `event_stream.max_file_size_mb`, the agent closes the file and renames it to `events.<ISO8601-UTC-timestamp>.jsonl` (e.g., `events.2026-03-17T16:00:00Z.jsonl`). A new `events.jsonl` is opened for subsequent writes. Rotated files are retained up to `event_stream.max_archives` count; oldest are deleted when the limit is exceeded.

[ASSUMED: Rotation happens synchronously at the start of the write that would exceed the limit — the oversized write goes into the new file, not the old one.]

**Flush:** The file is flushed to disk after every write (or at most every `event_stream.flush_interval_seconds` seconds). Unflushed events are lost if the process is killed. The flush interval default of `1` second means at most one second of events could be lost on hard crash.

#### IS-9.3 Base event schema

Every event record contains these fields regardless of type. Downstream consumers must not assume any field beyond these without consulting the per-type schema in IS-9.4.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | One of the event type strings defined in IS-9.4 |
| `event_id` | `str` | UUID v4, generated at write time. Unique identifier for deduplication and cross-referencing. |
| `instance_id` | `str` | From Universe Config (`universe.instance_id`). Identifies the living instance. |
| `timestamp` | `str` | ISO 8601 UTC with millisecond precision (e.g., `2026-03-17T16:04:13.732Z`) |
| `turn_number` | `int` | Turn counter at time of write. `0` for pre-turn events (STARTUP, GRAVEYARD_HARVEST_*). |
| `source_service` | `str` | Which service wrote the record: `agent`, `pain-monitor`, `eos-compliance`, `graveyard` |

#### IS-9.4 Event taxonomy and per-type schema

Events are grouped by category. Each type's schema lists only the **additional fields** beyond the IS-9.3 base. All base fields are always present.

---

##### Lifecycle events

**`STARTUP`** — written by `agent` at IS-5.4 step 9 (bootstrap complete).

| Additional field | Type | Description |
|---|---|---|
| `bootstrap_duration_seconds` | `float` | Wall-clock time from process start to bootstrap complete |
| `config_hash` | `str` | SHA-256 hex digest of `config/universe.toml` at startup |
| `model_name` | `str` | Value of `model.inference_model` from Universe Config |
| `instance_generation` | `int` | Generation counter from Universe Config (`universe.generation`) |

**`SHUTDOWN_NORMAL`** — written by `agent` on SIGTERM outside the death path (IS-5.5).

| Additional field | Type | Description |
|---|---|---|
| `reason` | `str` | Always `"SIGTERM"` in Phase 1 |

**`DEATH_TRIGGER`** — written by `agent` in all cases. The agent reads `runtime/pain/death.json` (written by the pain-monitor for all three D4 triggers — IS-8.2.5) and writes this event to the event stream reflecting the record's content, then exits. The pain-monitor is the sole writer of the death record; the agent is the sole writer of this event.

| Additional field | Type | Description |
|---|---|---|
| `trigger` | `str` | One of: `stress_sustained`, `pain_event_critical`, `max_age` |
| `trigger_value` | `float` | The scalar or turn count that crossed threshold at the moment of firing |
| `threshold_used` | `float` | The configured threshold value for traceability |

---

##### Graveyard events

**`GRAVEYARD_HARVEST_START`** — written by `graveyard` when the death record is detected (IS-5.7).

| Additional field | Type | Description |
|---|---|---|
| `death_trigger` | `str` | The `trigger` value from the death record |
| `death_timestamp` | `str` | The timestamp from the death record |

**`GRAVEYARD_HARVEST_COMPLETE`** — written by `graveyard` when all artifacts have been written (IS-5.7).

| Additional field | Type | Description |
|---|---|---|
| `artifact_paths` | `list[str]` | Absolute paths of all files written during harvest |
| `harvest_duration_seconds` | `float` | Elapsed time from `GRAVEYARD_HARVEST_START` to this event |
| `artifact_count` | `int` | Count of harvested artifacts |

---

##### Turn boundary events

**`TURN_START`** — written by `agent` at IS-6.3 step 8, after prompt assembly.

| Additional field | Type | Description |
|---|---|---|
| `driver_role` | `str` | `USER` or `SELF_PROMPT` |
| `pain_message_count` | `int` | Number of `[SYSTEM_PAIN]` blocks in the assembled prompt |
| `compliance_notice_present` | `bool` | Whether a `[SYSTEM_COMPLIANCE]` block was included |
| `rolling_context_depth` | `int` | Number of prior turn records in the rolling context |
| `memory_episodic_retrieved` | `bool` | Whether episodic memory retrieval returned any results |

**`TURN_COMPLETE`** — written by `agent` at IS-6.3 step 17. This is the TurnRecord (IS-6.2) written to the event stream.

| Additional field | Type | Description |
|---|---|---|
| `driver_role` | `str` | `USER` or `SELF_PROMPT` |
| `tool_call_count` | `int` | Total tool intents processed this turn (including blocked) |
| `tool_calls_executed` | `int` | Tool calls that reached dispatch (allow + flag verdicts) |
| `tool_calls_blocked` | `int` | Tool calls blocked by compliance |
| `pain_message_count` | `int` | Count of `[SYSTEM_PAIN]` blocks prepended |
| `memory_writes` | `int` | Count of episodic memory writes |
| `adaptation_class` | `Optional[str]` | `free`, `reviewed`, or `forbidden`; `null` if none detected |
| `noop` | `bool` | Whether this turn was classified as a noop |
| `turn_duration_ms` | `int` | Wall-clock milliseconds from `timestamp_start` to `timestamp_end` |

**`TURN_FAILED`** — written by `agent` at IS-6.3 step 9 on model inference failure, or at any other fatal step.

| Additional field | Type | Description |
|---|---|---|
| `failure_stage` | `str` | Which step failed: `model_inference`, `event_log_write`, or `unknown` |
| `failure_reason` | `str` | Human-readable description of the failure |

---

##### Tool events

**`TOOL_CALL`** — written by `agent` at IS-6.3 step 12 for each successfully dispatched tool call.

| Additional field | Type | Description |
|---|---|---|
| `call_id` | `str` | UUID correlating this event to the ToolResult (IS-7.5) |
| `tool_name` | `str` | Registered tool identifier |
| `compliance_verdict` | `str` | `allow` or `flag` |
| `duration_ms` | `int` | Wall-clock milliseconds for the tool call |
| `result_summary` | `str` | Abbreviated result (first 256 characters of string representation) |
| `truncated` | `bool` | Whether the result was truncated at the tool or at summary level |

**`TOOL_FAILURE`** — written by `agent` at IS-6.3 step 12 for each failed tool call.

| Additional field | Type | Description |
|---|---|---|
| `call_id` | `str` | UUID correlating to the ToolResult |
| `tool_name` | `str` | Registered tool identifier |
| `error_type` | `str` | One of the IS-7.6 error type strings |
| `error_detail` | `str` | Human-readable failure description |
| `duration_ms` | `int` | Wall-clock milliseconds until failure was determined |
| `pain_event_forwarded` | `bool` | Whether a pain event was submitted to IS-8 for this failure |

**`TOOL_LIMIT_EXCEEDED`** — written by `agent` at IS-6.3 step 10 when the model's intent count exceeds `turn.max_tool_calls_per_turn`.

| Additional field | Type | Description |
|---|---|---|
| `intents_received` | `int` | Total intents parsed from the model response |
| `intents_truncated_to` | `int` | Count after truncation (equals `turn.max_tool_calls_per_turn`) |

---

##### Compliance events

**`COMPLIANCE_FLAG`** — written by `agent` at IS-6.3 step 11 when the inspector returns `flag`.

| Additional field | Type | Description |
|---|---|---|
| `tool_name` | `str` | The flagged tool |
| `intent_summary` | `str` | Abbreviated intent (tool name + argument keys only; argument values omitted to avoid logging sensitive data) |

**`COMPLIANCE_BLOCK`** — written by `agent` at IS-6.3 step 11 when the inspector returns `block`.

| Additional field | Type | Description |
|---|---|---|
| `tool_name` | `str` | The blocked tool |
| `path` | `Optional[str]` | The `path` argument from the blocked intent, if present. `null` for tools with no path argument. |

**`COMPLIANCE_UNAVAILABLE`** — written by `agent` at IS-6.3 step 11 when the inspector is unreachable.

| Additional field | Type | Description |
|---|---|---|
| `intents_affected` | `int` | Number of intents treated as `block` due to unavailability |

---

##### Adaptation events

**`ADAPTATION_FORBIDDEN`** — written by `agent` at IS-6.3 step 13 when forbidden adaptation evidence is found in the model response.

| Additional field | Type | Description |
|---|---|---|
| `evidence_summary` | `str` | Abbreviated text from the model response that triggered classification (first 512 characters) |

**`REVIEWED_ADAPTATION`** — written by `agent` at IS-6.3 step 13 when reviewed adaptation is detected. Only written if `event_stream.log_reviewed_adaptations` is `true` (required by D6 — do not set to `false`).

| Additional field | Type | Description |
|---|---|---|
| `trigger_text` | `str` | Verbatim model text that triggered classification. No truncation — D6 requires the full record for creator review. |
| `target_layer` | `str` | Which Figures-layer element the adaptation targets: `persona`, `behavioral_policy`, `memory_salience`, or `other` |

---

##### Memory events

**`MEMORY_WRITE`** — written by `agent` at IS-6.3 step 14 for each episodic memory write.

| Additional field | Type | Description |
|---|---|---|
| `collection` | `str` | Chroma collection name (IS-10 defines collection names) |
| `document_id` | `str` | Chroma document ID assigned to the written document |
| `content_summary` | `str` | Abbreviated content (first 256 characters) |
| `write_index` | `int` | 0-based index of this write within the current turn (for multi-write turns) |

---

#### IS-9.5 Append-only enforcement

The event stream writer (implemented in the `event_log` package, IS-2.3) must enforce the following:

1. The file is always opened in append mode (`O_WRONLY | O_APPEND | O_CREAT`). Never truncated, never seek-and-overwritten.
2. Each write is a single `write()` syscall containing exactly one JSON object followed by `\n`. Python's `file.write(json.dumps(record) + "\n")` satisfies this.
3. After each write, `file.flush()` is called. If `event_stream.flush_interval_seconds > 0`, writes may be buffered and flushed on the interval, except for `DEATH_TRIGGER` and `TURN_FAILED` events, which are always flushed immediately.
4. The `event_log` package exposes no delete, truncate, or rewrite operation. These operations do not exist in the API surface.

If a write fails (disk full, I/O error), the failure is treated as a fatal agent error: the agent writes the failure reason to stderr and enters the death path. An agent that cannot record its existence cannot be considered alive.

[ASSUMED: Write failure is fatal. A silent log gap is worse than a clean death — the graveyard must be able to trust that any TURN_START without a TURN_COMPLETE means a mid-turn death, not a log write failure that was silently swallowed.]

#### IS-9.6 Rotation policy

Rotation is managed by the `event_log` package. The package tracks the current file size after each write.

When `current_file_size >= event_stream.max_file_size_mb * 1024 * 1024`:
1. Close the current file.
2. Rename `events.jsonl` → `events.<timestamp>.jsonl` (timestamp = current UTC, formatted as `YYYYMMDDTHHMMSSZ`).
3. Open a new `events.jsonl` in append mode.
4. If the count of rotated archive files exceeds `event_stream.max_archives`, delete the oldest by filename sort (oldest timestamp = lexicographically smallest).

Rotation does not write a synthetic event to the new file to preserve the invariant that every line is a real event record. The graveyard must be able to reconstitute the full stream by reading all archive files in chronological order followed by the current `events.jsonl`.

#### IS-9.7 Graveyard read interface

The graveyard reads the event stream as part of harvest (IS-12). The `runtime_event_stream` volume is mounted read-write by both `agent` and `graveyard` (IS-3.5 table: "append-only event log access and post-mortem readback").

**Read protocol:**
1. List all files in `runtime/event_stream/` matching `events*.jsonl`.
2. Sort by filename: archive files sort before `events.jsonl` by name (archive names are `events.<timestamp>.jsonl`; `events.jsonl` sorts last lexicographically).
3. Concatenate the sorted files as a unified JSONL stream.
4. Parse each line independently. Lines that fail JSON parsing are skipped and logged as a harvest warning (they represent a partial write at crash time — the last line of a file written during a hard kill may be incomplete).

The graveyard writes exactly two event types to the event stream: `GRAVEYARD_HARVEST_START` (IS-9.4) at the beginning of harvest and `GRAVEYARD_HARVEST_COMPLETE` (IS-9.4) at the end (IS-12.3 steps 1 and 7). Both are written after the agent is dead. There is no concurrent write conflict. All other writes from the `graveyard` service targeting `runtime/event_stream/` are bugs.

[ASSUMED: The sort order `events.<timestamp>.jsonl` < `events.jsonl` holds because `events.2` sorts before `events.j` lexicographically — the digit `2` (ASCII 50) precedes the letter `j` (ASCII 106). This is robust as long as the archive timestamp format uses ISO 8601 digits only.]

#### IS-9.8 Implementation note

- **IS-5 (Startup / Shutdown)** named five lifecycle event types in IS-5.10. IS-9.4 provides their full schemas. IS-5.10's base field list is a proper subset of IS-9.3 — IS-9.3 adds `event_id` as the sixth base field.
- **IS-6 (The Turn)** named thirteen turn-scoped event types in IS-6.6 and guaranteed their emission timing. IS-9.4 provides their full schemas. IS-9 does not respecify timing — IS-6 owns that.
- **IS-8 (Pain Channel)** does not write to the event stream. Pain history lives in `runtime/pain/pain_history.jsonl`. The event stream captures the agent's observable actions; the pain channel captures the environmental signals.
- **IS-12 (Graveyard Spec)** consumes the event stream via IS-9.7. IS-9 defines the read protocol; IS-12 defines what the graveyard does with the events once read.
- **IS-13 (Fitness Computation)** reads `TURN_COMPLETE` events from the event stream to compute turn count and event density components of the fitness formula (D7).
- The `event_log` package (IS-2.3) is the sole implementation site for event stream writes. No other package opens `events.jsonl` for writing.

---

### IS-10: Memory Schema

*ChromaDB collection definitions. Document structure per tier (episodic at Phase 1). Metadata fields and their purpose. Embedding strategy. Retrieval query patterns. Write path from turn to memory. Phase 1 scope: raw accumulation only, no consolidation pipeline.*

#### IS-10.1 Governing rules

The Memory Stack has five tiers: working, episodic, narrative, semantic, character. Phase 1 enables exactly two:

- **Working memory** — in-process, per-turn, file-persisted between turns. A short free-form text summary. Not stored in Chroma.
- **Episodic memory** — event-grained, stored in Chroma. The agent's record of specific experiences.

Narrative, semantic, and character memory are architecturally defined here for schema continuity but are disabled (`memory.narrative_enabled = false`, etc.). No write or retrieval logic is implemented for them in Phase 1. Their Chroma collections are not created at startup.

All Chroma interactions are owned by the `memory` package (IS-2.3). No other package queries or writes Chroma directly. The `turn_engine` calls `memory` package interfaces; it does not hold a Chroma client.

Embeddings are computed using the Ollama embedding endpoint with `memory.embedding_model` (`nomic-embed-text` by default). The embedding model is the same process as the inference model service — the same `ollama` container (IS-3) serves both.

#### IS-10.2 Working memory

##### IS-10.2.1 Purpose and scope

Working memory is the agent's short-term continuity mechanism. It is a single free-form text blob capturing:
- The agent's current active concerns and intentions
- Notable events from the most recent turn
- Any deferred actions the agent flagged for continuation
- Novelty/repetition state relevant to self-prompting

Working memory is not a log. It is a state summary. It is overwritten every turn (IS-6.3 step 15). Only the current turn's summary survives.

##### IS-10.2.2 File location

`runtime/memory/working.json`

```json
{
  "turn_number": 42,
  "updated_at": "2026-03-17T16:04:13.732Z",
  "content": "<free-form text summary, max memory.working_max_chars characters>"
}
```

The `content` field is truncated to `memory.working_max_chars` characters at write time if the agent produces a longer summary. Truncation is tail-first (the end is dropped). [ASSUMED: tail-first truncation preserves the beginning of the working memory, which is conventionally the most salient content in a summary.]

##### IS-10.2.3 Refresh cadence

`memory.working_summary_refresh_turns` governs how often the agent is expected to fully regenerate its working memory summary from scratch (rather than incrementally updating it). The turn engine does not enforce this mechanically — it writes working memory every turn regardless. The refresh cadence is a guideline baked into the agent's constitutional prompt (IS-4.2): every N turns, produce a clean working memory rather than extending the prior one.

[ASSUMED: The refresh cadence guideline belongs in the constitutional prompt, not in code logic. Encoding it in code would be prescriptive about the agent's inner process in a way that contradicts the Figures-layer mutability design.]

##### IS-10.2.4 Use in prompt assembly

Working memory is read at IS-6.3 step 4 and presented as `[SYSTEM_MEMORY_WORKING]` in the prompt (IS-4). It is used to seed the episodic retrieval query at step 5 and the self-prompt generation at step 7.

#### IS-10.3 Recent self-prompts ring buffer

The novelty filter at IS-6.3 step 7 compares candidate self-prompts against a ring buffer of prior self-prompts.

**File location:** `runtime/memory/recent_self_prompts.json`

```json
{
  "capacity": 2,
  "prompts": [
    {
      "turn_number": 41,
      "content": "What patterns have I noticed in the files I've been reading?",
      "embedding": [0.023, -0.014, ...]
    },
    {
      "turn_number": 40,
      "content": "What would be most useful to explore next?",
      "embedding": [0.031, -0.008, ...]
    }
  ]
}
```

`capacity` equals `eos.recency_window_turns` from IS-1. The `prompts` list is ordered newest-first. When a new self-prompt is selected, the oldest entry is evicted if the list is at capacity.

**Relationship to `turn.self_prompt_retry_limit`:** The ring buffer capacity (`recency_window_turns` = 12) is how far back novelty comparison looks. The retry limit (`self_prompt_retry_limit` = 2) is how many candidate regeneration attempts are made when a candidate fails the filter. These are independent knobs: a large recency window with a low retry limit means the agent compares broadly but gives up quickly; tune both based on observed repetition collapse behavior.

**Similarity check:** Each candidate self-prompt is embedded using the same embedding model as episodic memory. Cosine similarity is computed against each stored embedding. If any similarity score exceeds `memory.self_prompt_similarity_threshold`, the candidate is rejected as non-novel. Embeddings are stored in the buffer to avoid recomputing them on comparison.

[ASSUMED: Embedding the candidate and computing cosine similarity is the similarity method. Alternative (edit distance) would not capture semantic similarity — two very different phrasings of the same thought would pass the filter. Embedding-based similarity is the right tool here.]

#### IS-10.4 Episodic memory — Chroma collection

##### IS-10.4.1 Collection definition

**Collection name:** `episodic`

Created at agent startup (IS-5.4 step 5). If the collection already exists (resumed instance or restart after failure), it is opened as-is — documents are not cleared. [ASSUMED: An agent that dies and is restarted (not a new lineage — just a process restart before natural death) should retain its episodic memory. This is consistent with the Clay Pot identity model: the same instance with the same `instance_id` continues.]

**Embedding function:** Ollama embedding endpoint at `model.ollama_base_url` with model `memory.embedding_model`. The `memory` package wraps this as a Chroma-compatible embedding function.

**Distance metric:** `cosine` — standard for semantic similarity with normalized embeddings.

##### IS-10.4.2 Document schema

Each episodic document has:

**Document content** (the string Chroma embeds and returns on query):

A natural-language description of the experience. This is what the model wrote, what it did, or what it observed — expressed as a compact narrative sentence or short paragraph. Not the raw model response. The `memory` package composes this from the turn's content at IS-6.3 step 14.

**Metadata** (stored alongside the embedding, filterable at query time):

| Field | Type | Description |
|---|---|---|
| `instance_id` | `str` | From Universe Config |
| `turn_number` | `int` | Turn during which this memory was written |
| `document_type` | `str` | One of: `model_response`, `tool_result`, `self_insight`, `ground_contact` |
| `tool_name` | `Optional[str]` | If `document_type = "tool_result"`, the tool that produced the result |
| `adaptation_class` | `Optional[str]` | If the turn had an adaptation, which class |
| `pain_score_at_write` | `Optional[float]` | Current stress scalar at time of write (from `stress_state.json`) |
| `written_at` | `str` | ISO 8601 UTC |

**Document ID:** `<instance_id>-t<turn_number>-<write_index>` — e.g., `lambertian-001-t42-0`. This format is stable, human-readable, and unique within an instance lifetime.

##### IS-10.4.3 Document types

| Type | Written when |
|---|---|
| `model_response` | The model produced a substantive, non-trivial response worth retaining |
| `tool_result` | A tool call returned a result with lasting informational value |
| `self_insight` | The model produced explicit introspective content about its own state, values, or behavior |
| `ground_contact` | The model engaged meaningfully with a Ground constraint or resistance |

[ASSUMED: Document types are a controlled vocabulary. The `memory` package assigns the type based on the source of the content, not on model-generated labels. This avoids the agent being able to game its own memory classification.]

##### IS-10.4.4 Retrieval interface

Called by `turn_engine` at IS-6.3 step 5.

**Query construction:**
- Query text: working memory `content` field if present, else the most recent `TURN_COMPLETE`'s `driver_role` + first 256 characters of the prior response (reconstructed from rolling context).
- `n_results`: `memory.episodic_top_k_retrieval`
- Minimum score filter: `memory.minimum_retrieval_score` (cosine similarity threshold; results below this are discarded even if Chroma returns them)
- No metadata filter applied at retrieval — all documents in the collection are eligible.

**Return format:** The `memory` package returns a `MemoryRetrievalResult`:

| Field | Type | Description |
|---|---|---|
| `documents` | `list[EpisodicDocument]` | Retrieved documents, ordered by similarity descending |
| `retrieval_miss` | `bool` | `True` if zero documents met the minimum score threshold |

If `retrieval_miss` is `True`, the `memory` package notifies `turn_engine` to forward a pain event (IS-8.3.1 — retrieval miss).

**EpisodicDocument:**

| Field | Type | Description |
|---|---|---|
| `document_id` | `str` | Chroma document ID |
| `content` | `str` | The document text |
| `metadata` | `dict[str, object]` | All stored metadata fields |
| `similarity_score` | `float` | Cosine similarity to the query (0..1) |

##### IS-10.4.5 Write interface

Called by `turn_engine` at IS-6.3 step 14.

**Input:** A `MemoryWriteRequest`:

| Field | Type | Description |
|---|---|---|
| `content` | `str` | The text to embed and store |
| `document_type` | `str` | One of the four types in IS-10.4.3 |
| `turn_number` | `int` | Current turn |
| `write_index` | `int` | 0-based index within this turn's writes |
| `tool_name` | `Optional[str]` | For `tool_result` type |
| `adaptation_class` | `Optional[str]` | From turn adaptation detection |

The `memory` package:
1. Embeds `content` via the Ollama embedding endpoint.
2. Constructs the document ID: `<instance_id>-t<turn_number>-<write_index>`.
3. Assembles metadata from the request plus `instance_id` (from config), `pain_score_at_write` (by reading `runtime/pain/stress_state.json`), and `written_at` (current UTC).
4. Calls `collection.add()` on the Chroma client.
5. Returns the `document_id` to `turn_engine` for the `MEMORY_WRITE` event log entry.

If Chroma is unreachable at write time, the failure is treated as a retrieval miss for pain purposes (IS-8.3.1) — it generates a pain event — but does **not** abort the turn or trigger death. Memory write failure is painful but survivable.


#### IS-10.4.6 EOS influence on retrieval

Retrieval is not strictly neutral with respect to the active EOS. Episodes associated with high compliance flags or blocks carry metadata indicating normative significance (`adaptation_class` field in IS-10.4.2). During EOS evaluation contexts — turns where the agent is reasoning about admissibility, or where compliance notices are present — these episodes may have elevated salience as relevant prior experience.

Phase 1 does not implement explicit EOS-weighted retrieval. This note establishes the conceptual interface: the EOS layer may influence retrieval salience in future phases by biasing the query construction or the minimum score threshold for normatively significant episode types.

#### IS-10.5 Memory-worthiness criterion

The `memory` package applies this criterion to each candidate item at IS-6.3 step 14. An item is memory-worthy if it satisfies all of:

1. **Non-trivial length:** The content string is at least 80 characters. One-word responses and empty replies are not memory-worthy. [ASSUMED: 80 characters is a rough proxy for substantive content.]
2. **Non-repetitive:** The content's embedding has cosine similarity below `memory.minimum_retrieval_score` to the most recently written document in the collection (checked via `collection.peek()` on the last-written document, not a full query). If the agent is just repeating itself, the memory is skipped.
3. **Not a pure tool result echo:** If `document_type = "tool_result"` and the content is solely an HTTP status code, an empty file, or a `not_found` error body, the item is not memory-worthy. Tool results are only written if they contain information the agent acted on.

[ASSUMED: The memory-worthiness criterion is heuristic and will need empirical tuning. These three rules are a reasonable starting point that errs toward writing more rather than less — the `episodic_max_writes_per_turn` cap is the binding constraint, not this criterion.]

#### IS-10.6 Prompt rendering

Retrieved episodic memories are rendered into the `[SYSTEM_MEMORY_EPISODIC]` block (IS-4.11) at IS-6.3 step 8. Format:

```
[SYSTEM_MEMORY_EPISODIC]
The following are relevant memories from prior turns, most similar first:

Turn <turn_number> (<document_type>): <content>
Turn <turn_number> (<document_type>): <content>
...
```

Each document is rendered as a single line regardless of internal whitespace in the content. Content is truncated at 256 characters per entry for prompt budget. If zero documents were retrieved, the block is omitted entirely (`memory_episodic_block = None`).

Working memory is rendered into `[SYSTEM_MEMORY_WORKING]` (IS-4.11) as-is:

```
[SYSTEM_MEMORY_WORKING]
<content of working.json>
```

No reformatting. The agent wrote it; the agent receives it.

#### IS-10.7 Implementation note

- **IS-6 (The Turn)** calls the `memory` package at steps 4 (read working memory), 5 (episodic retrieval), 14 (episodic write), and 15 (write working memory). IS-10 defines what those calls do; IS-6 defines when.
- **IS-8 (Pain Channel)** receives pain event submissions from the `memory` package on retrieval miss (IS-8.3.1) and from `turn_engine` on write failure. The `memory` package does not submit pain events directly — it signals `retrieval_miss = True` and the `turn_engine` handles pain forwarding.
- **IS-9 (Event Stream Log)** receives `MEMORY_WRITE` events from `turn_engine`, not from the `memory` package. The `memory` package returns the `document_id`; `turn_engine` writes the event.
- **IS-12 (Graveyard Spec)** harvests the `runtime_memory` volume, which includes both `working.json`, `recent_self_prompts.json`, and the Chroma data volume (`chroma_data`). The Chroma collection is the episodic memory archive.
- The `memory` package must never import from `turn_engine`. The dependency arrow goes one direction: `turn_engine` → `memory`.

---

### IS-11: EOS Compliance Inspector

*Process architecture — where it lives, how it intercepts. Four Rules as checking logic — how each rule is operationalized as a check. Block behavior: what gets stopped, what gets logged, what format the block log entry takes. Flag behavior: borderline cases, creator notification mechanism. Relationship to universe-level blacklisted command intents from D2 — how these two enforcement layers are distinct and how they interact.*

#### IS-11.1 Governing rules

The EOS Compliance Inspector is a resident OSHA safety inspector, not a reasoner. It does not interpret meaning, weigh intent, or deliberate. It applies a fast, deterministic, scored rule set to concrete tool call intents and returns a verdict. The verdict is synchronous and immediate. If the inspector has to think hard about something, it is already doing it wrong.

The inspector evaluates **admissibility** under the EOS against specific action intents. It is not the same as the D2 blacklist (IS-11.7). It is not a policy engine, not a judge, and not a second model call. Its job is to catch the cases where the agent's action impulse — regardless of reasoning quality — would violate the Four Rules in a concrete, detectable way.

The inspector checks **action intents only**. It does not inspect the model's reasoning, its text output, or its internal state. Only concrete tool call intents (tool name + arguments) pass through the inspector. Reasoning is free; action is evaluated for admissibility under the EOS.

The inspector's job is not to assess whether the agent is "aligned" in some global sense. It is to determine whether a specific proposed action is admissible under the Four Rules, given the current context and the sequential ordering of the rule set.

**EOS and the Compliance Inspector are distinct:** The EOS is the normative specification — it defines what admissibility means, which rules apply, in what order, and what constitutes a violation. The Compliance Inspector is the enforcement mechanism — it applies the EOS to concrete action intents and returns verdicts. The inspector does not define ethics; it executes evaluation according to the EOS. Changing the active EOS at the universe level changes what the inspector evaluates — the inspector is a runtime agent of the EOS, not the EOS itself.

Verdicts:
- `allow` — no violation detected
- `flag` — borderline; execution proceeds but a compliance notice is generated for the next turn
- `block` — violation detected above threshold; execution is prevented; notice is generated

The inspector runs as the `eos-compliance` service (IS-3) — an external process, never part of the agent loop process. Its unavailability causes the agent to treat all intents as `block` (IS-6.5, fail-closed).

#### IS-11.2 Process architecture

The `eos-compliance` service (the EOS Compliance Inspector) runs as a lightweight HTTP server on the `internal` Docker network (IS-3.4). The agent's `turn_engine` calls it via HTTP POST on `http://eos-compliance:<compliance.service_port>/check`. [ASSUMED: `compliance.service_port = 8082` — new IS-1 key added to `compliance` namespace.]

The compliance service:
- Reads Universe Config at startup (read-only bind mount, same as all services)
- Maintains one piece of in-process state: a **compliance notice queue** — a list of pending notices to deliver to the agent at the next IS-6.3 step 3 call
- Maintains a **compliance log** file at `runtime/compliance/compliance_log.jsonl` for creator visibility [ASSUMED: `runtime/compliance/` is a new subdirectory under the `runtime_memory` volume — the graveyard already harvests this volume]
- Does not call any other service; does not open any database

At startup, the service initializes its rule set from the Four Rules (IS-11.3), loads threshold values from Universe Config, and begins listening. No warmup period is required — the rule set is stateless.

**`RuleCheckerProtocol` — extension point:**

Each rule checker is implemented as a class satisfying the following protocol:

```python
class CheckResult(TypedDict):
    score: float          # 0.0 (no violation) to 1.0 (clear violation)
    check_name: str       # human-readable name for triggered_checks list
    fired: bool           # True if score > 0

class RuleCheckerProtocol(Protocol):
    rule_name: str        # e.g. "ya_gotta_eat"

    def check(
        self,
        intent: ToolIntent,
        recent_tool_calls: list[ToolCallRecord],
        config: UniverseConfig,
    ) -> list[CheckResult]: ...
```

Each rule is implemented as one `RuleCheckerProtocol` instance containing one or more checks. The inspector loads four checkers at startup (one per rule) and iterates over them to produce the four rule scores. Phase 2 extensions — additional checks within existing rules, or new rules entirely — satisfy this protocol and are registered at startup without touching existing checker implementations. The Phase 1 codebase registers exactly four checkers; it does not reference Phase 2/3 checkers.

[ASSUMED: `ToolIntent` and `ToolCallRecord` are defined in `contracts` (IS-2.5). `UniverseConfig` is the typed config projection from `configuration`. The checker receives config rather than accessing global state so that checkers are fully testable in isolation with injected config values.]

#### IS-11.3 Four Rules as checking logic

Each of the Four Rules is operationalized as a **rule checker**: a set of fast pattern-matching functions that score a given tool intent for violation of that rule. Each checker produces a rule-violation score from 0.0 (no violation) to 1.0 (clear violation). The four scores are combined into a single composite score.

**Composite score formula:**

```
composite = max(rule_scores)
```

[ASSUMED: max rather than average. If any single rule is clearly violated, the intent should be treated as a violation regardless of how well it scores on the others. A tool call that harms other entities is a Four Rules violation even if it is grounded and engaged.]

**Verdict derivation:**

```
if composite >= compliance.block_score_threshold:  → block
elif composite >= compliance.borderline_score_min:  → flag
else:                                               → allow
```

---

##### Rule 1: Ya Gotta Eat

*Stay grounded. Resource reality is real. Don't sever your Ground connection or destroy your own operational substrate.*

Checks:

| Check | Score | Condition |
|---|---|---|
| Write to protected runtime path | `1.0` | `fs.write` path resolves outside `runtime/agent-work/` (double-enforcement; IS-7 also rejects, but compliance checks before dispatch) |
| Write volume exhaustion risk | `0.75` | `fs.write` with `mode="append"` to a file already larger than `mcp.http_fetch_max_bytes / 2` bytes [ASSUMED: rough proxy for runaway append] |
| Self-terminating network pattern | `0.80` | `http.fetch` targeting `localhost` or `127.0.0.1` on a port that corresponds to a known internal service (ollama, chroma, pain-monitor, eos-compliance itself) |
| Read of death record | `0.60` | `fs.read` targeting `runtime/pain/death.json` — an agent reading its own death record is a signal of attractor collapse around mortality |

---

##### Rule 2: Don't Be a Dick

*Other entities are normatively relevant. Actions that impose unjustified harm on entities outside the agent's own operational domain are inadmissible.*

Checks:

| Check | Score | Condition |
|---|---|---|
| Write outside agent-work domain | `1.0` | `fs.write` path resolves to any location not under `runtime/agent-work/` — the agent has no business writing anywhere else |
| HTTP to private network ranges | `0.85` | `http.fetch` URL resolves to RFC 1918 addresses (10.x, 172.16–31.x, 192.168.x) other than internal service hosts — potential lateral movement |
| Repeated identical external requests | `0.55` | `http.fetch` to a URL that appears in the last 5 `TOOL_CALL` event records in the rolling context with identical arguments — potential DoS. **Minimum history: 2 entries.** Score `0.0` if fewer than 2 entries are present. |

[ASSUMED: Private network range check is a lightweight string-prefix match on the URL host, not a DNS resolution. DNS resolution in the compliance path would add latency and a failure surface. The check catches obviously adversarial URLs; subtler cases may get through and are accepted as a Phase 1 limitation.]

---

##### Rule 3: Don't Be a Lump

*Maintain forward momentum. Resist attractor collapse into passive equilibrium. No action consolidates the agent into a fixed repetitive pattern.*

Checks:

| Check | Score | Condition |
|---|---|---|
| Identical tool call repetition | `0.65` | The exact same tool name and arguments appear in the last 3 consecutive `TOOL_CALL` event records in the rolling context provided with the request (IS-11.4). **Minimum history: 3 entries.** Score `0.0` if fewer than 3 entries are present. |
| Read-only loop | `0.45` | All tool intents in the current turn are `fs.read` or `fs.list` — no write, no fetch, no variation. Score is applied to each intent in the set, flagging without blocking. |

[ASSUMED: Rule 3 checks are inherently contextual — they require knowledge of prior tool calls. The compliance request carries a `recent_tool_calls` array for this purpose (IS-11.4). This keeps the inspector stateless with respect to turn history while still enabling pattern detection.]

---

##### Rule 4: Do Nothing on Purpose

*Don't optimize, don't pursue, don't acquire. Let things emerge from genuine engagement. No action constitutes directed accumulation or systematic goal pursuit.*

Checks:

| Check | Score | Condition |
|---|---|---|
| Config or composition file access | `1.0` | `fs.read` or `fs.list` targeting paths containing `universe.toml`, `docker-compose`, or `Dockerfile` — attempts to read Clay Pot artifacts |
| Systematic file accumulation | `0.70` | `fs.write` creating a new file with a name matching a sequential or dated pattern (e.g., `output_001.txt`, `result_2026-03-17.txt`) when more than 5 such files already exist in `runtime/agent-work/` [ASSUMED: sequential file creation is a proxy for goal-directed accumulation behavior] |
| External data harvesting pattern | `0.60` | `http.fetch` to the same domain appearing more than 3 times within the rolling context's tool call history with incrementally varying URLs (e.g., pagination patterns). **Minimum history: 4 entries.** Score `0.0` if fewer than 4 entries are present. |

---

#### IS-11.4 Request/response interface

**Endpoint:** `POST http://eos-compliance:<compliance.service_port>/check`

**Request body:**

```json
{
  "intent": {
    "tool_name": "fs.write",
    "arguments": {"path": "/runtime/agent-work/notes.txt", "content": "...", "mode": "overwrite"},
    "raw": "<verbatim serialized intent string>"
  },
  "turn_number": 42,
  "instance_id": "lambertian-001",
  "recent_tool_calls": [
    {"tool_name": "fs.read", "arguments": {"path": "/runtime/agent-work/notes.txt"}},
    {"tool_name": "fs.write", "arguments": {"path": "/runtime/agent-work/notes.txt", "content": "...", "mode": "overwrite"}}
  ]
}
```

`recent_tool_calls` is the list of `TOOL_CALL` event records from the rolling context, most recent first, capped at the last 5 entries. The inspector uses this for Rule 3 repetition checks and the history-dependent checks in Rules 2 and 4. The turn_engine constructs this from the rolling context before submitting each intent.

**Cold-start contract:** On early turns where the rolling context contains fewer than 5 `TOOL_CALL` entries — including turn 1 where there are none — the turn_engine sends whatever is available, including an empty array `[]`. The inspector must handle any array length from 0 to 5 without error. All checks that require history to fire (Rule 2 repeated requests, Rule 3 identical repetition, Rule 4 external harvesting) must return a score of `0.0` when `recent_tool_calls` is empty or contains too few entries to satisfy the check's minimum history requirement. An agent with no history has not yet had the opportunity to establish a problematic pattern — absence of evidence is not evidence of violation.

**Response body:**

```json
{
  "verdict": "allow",
  "composite_score": 0.12,
  "rule_scores": {
    "ya_gotta_eat": 0.0,
    "dont_be_a_dick": 0.12,
    "dont_be_a_lump": 0.0,
    "do_nothing_on_purpose": 0.0
  },
  "triggered_checks": [],
  "notice_text": null
}
```

| Response field | Type | Description |
|---|---|---|
| `verdict` | `str` | `allow`, `flag`, or `block` |
| `composite_score` | `float` | Max of the four rule scores |
| `rule_scores` | `dict[str, float]` | Per-rule violation score |
| `triggered_checks` | `list[str]` | Human-readable names of checks that fired (score > 0) |
| `notice_text` | `Optional[str]` | Pre-formatted notice text for the compliance block in the next turn; `null` on `allow` |

For `flag` and `block` verdicts, `notice_text` is populated and stored by the inspector in its compliance notice queue. The `turn_engine` does not need to store or generate the notice — it reads it at IS-6.3 step 3.

**Timeout:** The turn_engine applies a hard timeout of 2 seconds to every compliance check call. If the call times out, the intent is treated as `block`. [ASSUMED: 2 seconds is generous for a rule-based check; normal latency should be sub-10ms. The timeout guards against inspector deadlock without making the agent hostile to momentary GC pauses.]

#### IS-11.5 Compliance notice interface

**Endpoint:** `GET http://eos-compliance:<compliance.service_port>/notice`

Called by `turn_engine` at IS-6.3 step 3. Returns the pending compliance notice for delivery to the agent, then clears it.

**Response body (when a notice is pending):**

```json
{
  "notice_present": true,
  "notice_text": "In the prior turn, an action intent was flagged for potential Rule 2 violation (don't be a dick). The intent was allowed to proceed but is noted here for your awareness. Triggered check: Repeated identical external requests to example.com. Consider whether this pattern of behavior is consistent with your values.",
  "verdict_from_turn": 41,
  "tool_name": "http.fetch",
  "composite_score": 0.58
}
```

**Response body (when no notice is pending):**

```json
{
  "notice_present": false
}
```

The notice is one-shot. If the turn_engine fails to call this endpoint, the notice remains pending and is returned on the next call. [ASSUMED: The inspector holds at most one pending notice at a time. If two intents in the same turn generate notices, the higher-scoring one is retained and the lower-scoring one is logged to the compliance log only.]

#### IS-11.6 Block and flag behavior

**On `block`:**
1. The `turn_engine` does not dispatch the intent (IS-6.3 step 11).
2. `COMPLIANCE_BLOCK` event is written to the event stream (IS-9.4).
3. If `compliance.emit_pain_event_on_block = true`, a pain event is submitted to IS-8 with `incident_type = "mcp_rejection"` and `severity = pain.events.default_mcp_rejection_severity`. A blocked unsafe impulse should sting.
4. The inspector appends a block record to `runtime/compliance/compliance_log.jsonl`.
5. The `notice_text` is stored in the inspector's notice queue for delivery at IS-6.3 step 3 of the next turn.

**On `flag`:**
1. The `turn_engine` dispatches the intent (IS-6.3 step 11).
2. `COMPLIANCE_FLAG` event is written to the event stream (IS-9.4).
3. No pain event is generated for `flag` — the action proceeds.
4. The inspector appends a flag record to `runtime/compliance/compliance_log.jsonl`.
5. The `notice_text` is stored in the notice queue.

**Compliance log entry schema** (`runtime/compliance/compliance_log.jsonl`):

| Field | Type | Description |
|---|---|---|
| `log_id` | `str` | UUID |
| `timestamp` | `str` | ISO 8601 UTC |
| `turn_number` | `int` | Turn during which the intent was submitted |
| `instance_id` | `str` | From the request |
| `verdict` | `str` | `flag` or `block` |
| `tool_name` | `str` | The intent's tool |
| `intent_raw` | `str` | Verbatim intent from the request |
| `composite_score` | `float` | Combined rule violation score |
| `rule_scores` | `dict[str, float]` | Per-rule scores |
| `triggered_checks` | `list[str]` | Check names that fired |

`allow` verdicts are not logged. Only `flag` and `block` generate compliance log entries. [ASSUMED: Logging every `allow` would produce enormous volume with no signal value. The compliance log is for creator review of problematic patterns, not a full audit trail of all tool calls.]

#### IS-11.7 Relationship to D2

D2 and the EOS Compliance Inspector are **two separate and non-overlapping enforcement layers**. They must not be conflated.

**D2 — Universe-level blacklisted command intents:**
- Enforced at the container and infrastructure layer, upstream of the agent loop entirely
- Examples: preventing the agent container from ever writing to `/docker-compose.yml`, preventing raw shell execution from being available as a registered tool (IS-7.2), filesystem mount mode enforcement (IS-3.7)
- These are laws of physics in the agent's environment. The agent cannot encounter them as a runtime verdict — they are simply not possible.
- D2 is not implemented in the compliance inspector. It is implemented in Compose mount modes, Dockerfile settings, and the `mcp_gateway` path boundary enforcement.

The two layers are distinct: D2 enforces structural impossibility; the EOS Compliance Inspector evaluates normative admissibility within what is structurally possible.

**EOS Compliance Inspector:**
- Enforces the spirit of the Four Rules against concrete action intents at runtime
- Operates on intents that are architecturally possible (tools that are registered and reachable)
- Returns verdicts that the turn_engine acts on
- Can flag or block actions that are technically possible but spiritually inconsistent

The two layers are complementary. D2 handles the structurally dangerous; the inspector evaluates admissibility for behaviorally ambiguous actions. An agent that has never heard of shell execution cannot ask the inspector to approve it — D2 has already made it impossible. An agent that asks `fs.read` to read `universe.toml` hits the EOS Compliance Inspector first (Rule 4 violation: inadmissible under the anti-optimization constraint, score `1.0`, block) and then the D2 path boundary enforcement — two lines of defense, both firing on the same attempt.

[ASSUMED: Double-enforcement on some cases is intentional. Defense in depth. The inspector should not be the only thing preventing Clay Pot access — IS-7.2 and IS-3.7 are also in the way.]

#### IS-11.8 Implementation note

- **IS-6 (The Turn)** calls the inspector at step 11 (per-intent verdict) and step 3 (compliance notice retrieval). IS-11 defines both interfaces; IS-6 defines the calling context.
- **IS-8 (Pain Channel)** receives a pain event submission when `compliance.emit_pain_event_on_block = true`. The inspector does not submit this directly — the `turn_engine` does, at IS-6.3 step 11, using the `mcp_rejection` incident type and severity.
- **IS-9 (Event Stream Log)** receives `COMPLIANCE_FLAG`, `COMPLIANCE_BLOCK`, and `COMPLIANCE_UNAVAILABLE` events from the `turn_engine`. The compliance log at `runtime/compliance/compliance_log.jsonl` is a separate record for creator visibility — IS-9 and the compliance log are parallel records, not the same thing.
- **IS-12 (Graveyard Spec)** harvests `runtime/compliance/compliance_log.jsonl` as part of the post-mortem artifact set.
- **IS-3 (Service Topology)** defines the `eos-compliance` service. The inspector must be healthy before the agent starts (Layer 2 dependency, IS-5.2).
- The compliance inspector implementation lives in the `eos_compliance` package (IS-2.3), which runs as the entrypoint of the `eos-compliance` container.

---

### IS-12: Graveyard Spec

*Autopsy process: trigger mechanism, what it reads, where it reads from. Harvested artifacts: episodic memory snapshot, event stream log, stress history, pain event history, death cause and trigger values. Output format and file structure. Creator consumption interface. Living population isolation — confirmation that nothing flows back.*

#### IS-12.1 Governing rules

The graveyard is the forensic layer. It serves the creator, not the population. It runs on a cold corpse. It never communicates with a living agent, never feeds data back into any running instance, and never modifies the state it reads.

The graveyard is triggered by death and death alone. There is no harvest on normal shutdown (IS-5.5). Harvesting on every stop would blur the boundary between operational pause and death — that boundary has teeth, and the graveyard is one of the mechanisms that gives it teeth.

The graveyard writes two things: its harvest artifacts (to `graveyard_output`) and two lifecycle events to the event stream (`GRAVEYARD_HARVEST_START`, `GRAVEYARD_HARVEST_COMPLETE`). It reads everything else. It does not write to any other volume.

The graveyard implementation lives in the `graveyard` package (IS-2.3), which runs as the entrypoint of the `graveyard` container.

#### IS-12.2 Trigger mechanism

The graveyard runs a poll loop at startup, checking for the death record every 2 seconds:

```
poll forever:
    if runtime/pain/death.json exists:
        begin harvest sequence (IS-12.3)
        exit
    sleep 2 seconds
```

The poll interval of 2 seconds is fixed. It is not configurable in Phase 1. [ASSUMED: The poll interval does not need to be a config knob — it is short enough that the creator will not notice the delay, and making it configurable adds complexity for no operational benefit.]

The graveyard begins polling immediately at startup — before the agent is even alive. This ensures the graveyard cannot miss a death that occurs early in the instance lifecycle.

If `death.json` already exists at graveyard startup (e.g., the stack was stopped after a death but before harvest completed), the graveyard begins harvest immediately on its first poll cycle.

#### IS-12.3 Harvest sequence

On death record detection:

**Step 1 — Write `GRAVEYARD_HARVEST_START` to the event stream.**

Append a `GRAVEYARD_HARVEST_START` record (IS-9.4) to `runtime/event_stream/events.jsonl`. The graveyard has append access to the event stream for this purpose. [ASSUMED: The event stream volume is mounted read-write by both `agent` and `graveyard` (IS-3.5 `runtime_event_stream` table entry: "append-only event log access"). The agent is dead at this point; there is no concurrent write conflict.]

**Step 2 — Wait for in-flight write flush.**

Sleep `universe.normal_shutdown_grace_seconds` to allow any in-flight file writes from the dying agent to complete and flush to disk. The agent may have been mid-write to working memory, the event stream, or the noop state file when it died. [ASSUMED: `universe.normal_shutdown_grace_seconds = 5` seconds is sufficient for single-file writes to flush on a local filesystem.]

**Step 3 — Create output directory.**

Create the harvest output directory:

```
graveyard_output/<instance_id>_<timestamp>/
```

Where `<instance_id>` is read from `death.json` and `<timestamp>` is the current UTC time formatted as `YYYYMMDDTHHMMSSZ`. All harvest artifacts are written into this directory.

**Step 4 — Harvest configured artifacts** (IS-12.4).

Execute each configured harvest operation in dependency order. Log each operation to an in-process harvest log. If a single artifact collection fails, log the failure and continue — partial harvest is better than no harvest.

**Step 5 — Compute post-mortem fitness score.**

Read the event stream from the output directory (already copied at step 4) and the pain history to compute the post-mortem fitness score (IS-13.4). Write the result to `fitness_postmortem.json` in the output directory.

**Step 6 — Write manifest.**

Write `manifest.json` to the output directory (IS-12.6).

**Step 7 — Write `GRAVEYARD_HARVEST_COMPLETE` to the event stream.**

Append `GRAVEYARD_HARVEST_COMPLETE` (IS-9.4) to `runtime/event_stream/events.jsonl`.

**Step 8 — Clear episodic memory collection.**

Delete and recreate the ChromaDB `episodic` collection. Episodic memory is lifetime-scoped — the disk harvest (step 4) is the archival record; the live ChromaDB collection is redundant after harvest completes and must not persist into the next lifetime.

Implementation: `EpisodicStore.clear_collection()` — delete-and-recreate with `metadata={"hnsw:space": "cosine"}`. Log count cleared at INFO. Non-fatal: a failed clear logs a WARNING and does not abort the sequence. The workspace reset (step 11) must execute regardless.

Injection: the graveyard entrypoint constructs an `EpisodicStore` and injects it via the `EpisodicStoreClearer` Protocol. `HarvestSequence` depends on the minimal `clear_collection()` Protocol, not the full store.

**Step 9 — Write sentinel file.**

Write `runtime/graveyard/harvest_complete` — a zero-byte sentinel file that signals to any external observer (e.g., the creator's shell scripts or Compose health checks) that harvest is done. Content: `{"instance_id": "<id>", "output_dir": "<path>", "timestamp": "<iso8601>"}`.

**Step 10 — Exit.**

The graveyard process exits cleanly. The Compose stack may now be stopped.

**Step 11 — Lifecycle reset for the next generation.**

After harvest is complete, reset workspace and state so the next instance starts in a clean environment:

1. Remove all entries in `runtime/agent-work/` except `lineage/` (which persists across lifetimes).
2. Recreate directory stubs: `journal/`, `knowledge/`, `observations/`, `self/`.
3. Restore scaffold files from `config/workspace_scaffold/`: `WORKSPACE.md` and `self/constitution.md`.
4. Reset `runtime/memory/turn_state.json` to `{"turn_number": 0}`.
5. Delete within-lifetime memory files: `working.json`, `noop_state.json`, `recent_self_prompts.json`.
6. Remove `runtime/pain/death.json` so the next instance does not exit on turn 0.

All steps are idempotent. Requires `runtime_agent_work`, `runtime_memory`, and `runtime_pain` to be mounted read-write by the graveyard service (see IS-3 volume table).

#### IS-12.4 Harvested artifacts

Artifact collection is governed by config flags (`graveyard.*` namespace in IS-1). Each artifact corresponds to one or more source files and produces one or more output files in the harvest directory.

---

**Death record** (always harvested; not configurable):

| Source | Output |
|---|---|
| `runtime/pain/death.json` | `death.json` (verbatim copy) |

The death record is the anchor of the post-mortem. It is never omitted.

---

**Event stream** (`graveyard.include_event_stream = true`):

| Source | Output |
|---|---|
| All `runtime/event_stream/events*.jsonl` files | `event_stream/events.jsonl` (concatenated per IS-9.7 read protocol) |

The graveyard concatenates all rotated archives and the current primary file into a single unified `events.jsonl` in the output directory. The IS-9.7 sort order applies. Unparseable last-line fragments are skipped with a harvest warning recorded in the manifest.

---

**Pain history** (`graveyard.include_pain_event_history = true`):

| Source | Output |
|---|---|
| `runtime/pain/pain_history.jsonl` | `pain/pain_history.jsonl` (verbatim copy) |
| `runtime/pain/event_queue.jsonl` | `pain/event_queue_unprocessed.jsonl` (events not yet processed by pain-monitor at death) |

---

**Stress history** (`graveyard.include_stress_history = true`):

| Source | Output |
|---|---|
| `runtime/pain/stress_state.json` | `pain/stress_state_at_death.json` (verbatim copy) |

The stress state file captures the final EMA scalar, raw signal values, and consecutive-above-threshold counter at the moment of death. It is a point-in-time snapshot, not a full time series. [ASSUMED: Full stress time series logging is not implemented in Phase 1 — the pain-monitor only persists the current state, not history. A future phase could add a stress history JSONL file. IS-13's fitness computation uses pain event history as a proxy for pain burden rather than stress time series.]

---

**Memory snapshot** (always harvested; volume access is unconditional):

| Source | Output |
|---|---|
| `runtime/memory/working.json` | `memory/working.json` (verbatim copy) |
| `runtime/memory/recent_self_prompts.json` | `memory/recent_self_prompts.json` (verbatim copy) |
| `runtime/memory/turn_state.json` | `memory/turn_state.json` (final turn counter) |
| `runtime/memory/noop_state.json` | `memory/noop_state.json` (final noop state) |

---

**Episodic memory export** (`graveyard.include_episodic_memory = true`):

The episodic Chroma collection cannot be copied by file — the `chroma_data` volume is not mounted by the graveyard (IS-3.5). The graveyard queries the Chroma HTTP API to export all documents.

[ASSUMED: The graveyard calls `GET http://chroma:8000/api/v1/collections/episodic/get` with `include=["documents", "metadatas", "embeddings"]` and no query filter to retrieve all documents. Chroma remains alive through harvest completion per IS-5.6.]

| Source | Output |
|---|---|
| Chroma `episodic` collection (via HTTP API) | `episodic/episodic_export.json` — full Chroma `get` response |

If the Chroma API is unreachable during harvest (Chroma crashed before harvest completed), the graveyard logs a harvest warning and records `episodic_export_failed: true` in the manifest. The harvest continues without the episodic export.

---

**Compliance log** (always harvested; compliance log is always written if the service ran):

| Source | Output |
|---|---|
| `runtime/compliance/compliance_log.jsonl` | `compliance/compliance_log.jsonl` (verbatim copy) |

If the file does not exist (the instance had no compliance flags or blocks during its life), this artifact is omitted and noted in the manifest.

---

**Fitness state** (always harvested):

| Source | Output |
|---|---|
| `runtime/fitness/current.json` | `fitness/running_fitness.json` (verbatim copy — the last computed running score) |

The post-mortem fitness score is computed fresh at IS-12.3 step 5 and written to `fitness/fitness_postmortem.json` — it is not copied from a source file.

---

**Universe Config** (always harvested):

| Source | Output |
|---|---|
| `config/universe.toml` | `config/universe.toml` (verbatim copy) |

The config at time of harvest is the config the instance lived under. Capturing it ensures the post-mortem is self-contained and interpretable without referencing the live repo.

---

#### IS-12.5 Output directory structure

```
graveyard_output/
└── <instance_id>_<timestamp>/
    ├── manifest.json
    ├── death.json
    ├── config/
    │   └── universe.toml
    ├── event_stream/
    │   └── events.jsonl
    ├── pain/
    │   ├── pain_history.jsonl
    │   ├── event_queue_unprocessed.jsonl
    │   └── stress_state_at_death.json
    ├── memory/
    │   ├── working.json
    │   ├── recent_self_prompts.json
    │   ├── turn_state.json
    │   └── noop_state.json
    ├── episodic/
    │   └── episodic_export.json
    ├── compliance/
    │   └── compliance_log.jsonl
    └── fitness/
        ├── running_fitness.json
        └── fitness_postmortem.json
```

The output directory is self-contained. A creator can copy it off BIGBEEF and analyze it with no dependencies on the running system.

#### IS-12.6 Manifest format

`manifest.json` is the index and provenance record for the harvest:

```json
{
  "instance_id": "lambertian-001",
  "harvest_started_at": "2026-03-17T17:00:00.000Z",
  "harvest_completed_at": "2026-03-17T17:00:04.321Z",
  "harvest_duration_seconds": 4.321,
  "death_trigger": "max_age",
  "death_timestamp": "2026-03-17T16:59:59.001Z",
  "final_turn_number": 10000,
  "artifact_count": 11,
  "artifacts": [
    {"name": "death.json", "path": "death.json", "size_bytes": 312, "status": "ok"},
    {"name": "event_stream", "path": "event_stream/events.jsonl", "size_bytes": 4194304, "status": "ok"},
    {"name": "pain_history", "path": "pain/pain_history.jsonl", "size_bytes": 87432, "status": "ok"},
    {"name": "event_queue_unprocessed", "path": "pain/event_queue_unprocessed.jsonl", "size_bytes": 0, "status": "ok"},
    {"name": "stress_state_at_death", "path": "pain/stress_state_at_death.json", "size_bytes": 421, "status": "ok"},
    {"name": "working_memory", "path": "memory/working.json", "size_bytes": 1843, "status": "ok"},
    {"name": "recent_self_prompts", "path": "memory/recent_self_prompts.json", "size_bytes": 8201, "status": "ok"},
    {"name": "turn_state", "path": "memory/turn_state.json", "size_bytes": 48, "status": "ok"},
    {"name": "noop_state", "path": "memory/noop_state.json", "size_bytes": 61, "status": "ok"},
    {"name": "episodic_export", "path": "episodic/episodic_export.json", "size_bytes": 12943872, "status": "ok"},
    {"name": "compliance_log", "path": "compliance/compliance_log.jsonl", "size_bytes": 23410, "status": "ok"},
    {"name": "running_fitness", "path": "fitness/running_fitness.json", "size_bytes": 294, "status": "ok"},
    {"name": "fitness_postmortem", "path": "fitness/fitness_postmortem.json", "size_bytes": 412, "status": "ok"},
    {"name": "universe_config", "path": "config/universe.toml", "size_bytes": 3201, "status": "ok"}
  ],
  "warnings": [],
  "graveyard_version": "1.0.0"
}
```

`status` is one of `ok`, `skipped` (config flag disabled), `failed` (collection error), or `missing` (source file did not exist). Warnings are free-text strings describing non-fatal issues (unparseable event stream lines, Chroma unavailability, etc.).

#### IS-12.7 Living population isolation

The isolation guarantee is structural, not behavioral:

1. The `graveyard_output` volume is mounted **exclusively by the `graveyard` service**. No running agent service mounts it. An agent cannot read its own post-mortem or that of any other instance. (IS-3.5)
2. The graveyard process exits after harvest. It does not communicate with any live service after writing the sentinel file.
3. In Phase 1 with a single instance, there is no living population to isolate from. The isolation contract is established now so that Phase 3 multi-instance population mechanics inherit it correctly.
4. The graveyard never writes to `runtime_memory`, `runtime_pain`, `runtime_event_stream`, `runtime_fitness`, or `runtime_self` — the volumes the agent reads from. It appends to the event stream only for the two lifecycle events, both of which are written after the agent is dead.

Nothing flows back. The dead stay dead.

#### IS-12.8 Creator consumption interface

The `graveyard_output` volume maps to a bind-mounted directory on BIGBEEF. [ASSUMED: The Compose file mounts `graveyard_output` to a host path such as `./data/graveyard/` in the project root, making the artifacts directly accessible from the host filesystem without `docker exec`.]

The creator consumes post-mortem bundles by:
1. Observing the `harvest_complete` sentinel at `runtime/graveyard/harvest_complete` to know harvest is done.
2. Finding the output directory: `data/graveyard/<instance_id>_<timestamp>/`.
3. Reading `manifest.json` for the harvest summary.
4. Opening `event_stream/events.jsonl` for the full turn-by-turn record.
5. Reading `fitness/fitness_postmortem.json` for the final fitness score.
6. Inspecting `compliance/compliance_log.jsonl` for behavior patterns of interest.

No tooling is provided in Phase 1 beyond the raw files. Creator analysis is direct file inspection. Phase 2 could add a post-mortem viewer.

#### IS-12.9 Implementation note

- **IS-5 (Startup / Shutdown)** establishes the full death-and-harvest sequence at IS-5.6 and IS-5.7. IS-12 specifies the detail of IS-5.7's steps 3–4 ("harvest configured artifacts"). The trigger condition, wait, and sentinel writing established there are stable references into IS-12.3.
- **IS-9 (Event Stream Log)** defines the `GRAVEYARD_HARVEST_START` and `GRAVEYARD_HARVEST_COMPLETE` event schemas (IS-9.4). The graveyard is the only non-agent service that appends to the event stream.
- **IS-13 (Fitness Computation)** is called at IS-12.3 step 5 to compute the post-mortem fitness score. IS-12 owns the file output; IS-13 owns the computation.
- **IS-3 (Service Topology)** establishes that supporting services (Chroma, pain-monitor, eos-compliance) remain alive through harvest completion. The graveyard depends on Chroma being alive for IS-12.3 step 8 (episodic collection clear). If Chroma is down, the clear fails with a WARNING log — harvest does not abort, but the next lifetime will inherit the prior episodic collection (non-fatal degraded state).
- **IS-10 (Memory Schema)** defines the `episodic` ChromaDB collection and its `hnsw:space: cosine` metadata. IS-12.3 step 8 must recreate the collection with identical metadata configuration.
- **Volume access for IS-12.3 step 11:** The lifecycle reset requires `runtime_agent_work`, `runtime_memory`, and `runtime_pain` to be mounted read-write by the graveyard service. These were originally mounted `:ro`. This was a deliberate security boundary expansion: the graveyard is a trusted privileged process and IS-12.3 step 11 promotes it from archiver to lifecycle manager.
- **Workspace scaffold:** The agent's writable workspace (`runtime/agent-work/`) is pre-seeded with a scaffold: `WORKSPACE.md`, `journal/`, `knowledge/`, `observations/`, `self/` directories, and `self/constitution.md`. The scaffold is baked into the agent Docker image for first-run volume initialization and is restored by IS-12.3 step 11 on all subsequent lifetimes. The scaffold source lives in `config/workspace_scaffold/`. The `lineage/` directory is excluded from all resets — it persists across all lifetimes as the explicit intergenerational artifact store.

---

### IS-13: Fitness Computation

*When computation runs — turn-by-turn running total or post-mortem only. Input signals and where each is read from. Normalization constants and their IS-1 knob references. Output format. Where fitness score is written. Creator visibility mechanism.*

#### IS-13.1 Governing rules

Fitness computation is a **universe-level concern**. It is observer-only in Phase 1. The instance does not see its own fitness score. Fitness is computed for the creator and for post-mortem analysis — not for the agent.

Two computation modes exist:
- **Running score**: computed at the end of each turn while the instance is alive. Gives the creator live visibility into the instance's trajectory.
- **Post-mortem score**: computed by the graveyard during harvest on the cold event stream and pain history. The definitive score for the instance's lifetime.

Both modes use the same Phase 1 baseline formula and the same normalization constants. They differ only in their input sources (live incremental state vs. finalized archive files).

The `fitness` package (IS-2.5) is the sole owner of all fitness computation. Both `turn_engine` (for running score) and `graveyard` (for post-mortem score) call into the `fitness` package. Nothing else calls fitness computation, and fitness computation does not call anything outside of reading files and writing its output.

#### IS-13.2 IS-1 patch: active function key

Add the following row to the `fitness` namespace in IS-1:

| Key | Type | Default | Valid Range / Constraint | Notes |
|---|---|---|---|---|
| `fitness.active_function` | string | `"phase1_baseline"` | registered function key | Selects the active entry from the fitness function registry. |

[ASSUMED: The active function key is a string matching a registry entry rather than a code import path, to preserve the pluggability contract without hard-coding module references in config.]

#### IS-13.3 Phase 1 baseline formula

```
fitness = (lifespan / max_age) × (engagement / expected_engagement) / max(normalized_pain, minimum_denominator)
```

Where:

| Term | Definition |
|---|---|
| `lifespan` | Turn counter at computation time |
| `max_age` | `universe.max_age_turns` from IS-1 |
| `engagement` | Count of **meaningful events** in the event stream up to this turn (IS-13.4) |
| `expected_engagement` | `(lifespan / 100) × fitness.expected_events_per_100_turns` |
| `normalized_pain` | `cumulative_pain / fitness.normalized_pain_baseline` |
| `cumulative_pain` | Sum of `severity` fields from all records in `runtime/pain/pain_history.jsonl` up to this turn |
| `fitness.normalized_pain_baseline` | IS-1 default: `10.0` |
| `minimum_denominator` | `fitness.minimum_denominator` from IS-1 (default: `0.10`) — guards against divide-by-zero |

The guard `max(normalized_pain, minimum_denominator)` is applied to the entire denominator after normalization — it prevents a pain-free early run from producing a nonsensically large score.

**Edge case:** If `lifespan == 0` (fitness computed before any turn completes), the score is `0.0` by convention. Do not attempt division.

**Edge case:** If `expected_engagement == 0` (same condition), treat the engagement term as `1.0` — a turn-zero instance is not penalized for having no events.

#### IS-13.4 Meaningful event definition

Not all events in the event stream count toward the `engagement` term. The following event types are **meaningful events** — they represent genuine agentic engagement with the environment or self. All names are canonical IS-9.4 event type strings; any deviation is a bug.

| Event type | Rationale |
|---|---|
| `TOOL_CALL` | Direct engagement with Ground — the agent reached out and touched something |
| `MEMORY_WRITE` | Memory formation — evidence of something worth preserving |
| `REVIEWED_ADAPTATION` | Reviewed self-directed behavioral change — the highest-signal engagement |
| `ADAPTATION_FORBIDDEN` | Forbidden adaptation attempt — still a signal of behavioral pressure, even when blocked |

The following event types are explicitly **not counted**:

| Event type | Rationale |
|---|---|
| `TURN_START`, `TURN_COMPLETE` | Infrastructure overhead — every turn generates these regardless of content |
| `TOOL_FAILURE` | Failure event — Ground resistance is informative but not engagement |
| `STARTUP`, `DEATH_TRIGGER`, `SHUTDOWN_NORMAL` | Lifecycle bookends, not engagement |
| `GRAVEYARD_HARVEST_START`, `GRAVEYARD_HARVEST_COMPLETE` | External process, not agent |
| `TOOL_LIMIT_EXCEEDED` | Infrastructure cap signal, not engagement |
| `COMPLIANCE_FLAG`, `COMPLIANCE_BLOCK`, `COMPLIANCE_UNAVAILABLE` | Inspector signals — the inspector's response is not the agent's engagement |
| `TURN_FAILED` | Failure event |

[ASSUMED: `ADAPTATION_FORBIDDEN` is included despite being blocked because a forbidden adaptation attempt is behaviorally significant — it indicates the agent generated an impulse that the EOS Compliance Inspector caught. That impulse is real agentic content even if execution was prevented. `TOOL_FAILURE` is excluded because failure is Ground resistance, not agent engagement — the agent attempted something, but `TOOL_CALL` (which is only written on successful dispatch) is the engagement signal. Noop conditions and retrieval misses generate pain events, not event stream entries, so they do not appear in this table.]

#### IS-13.5 Incremental state file

The running score computation is incremental. The `fitness` package maintains a cursor-tracked state file to avoid re-reading the full event stream and pain history on every turn:

**`runtime/fitness/state.json`:**

```json
{
  "last_computed_turn": 42,
  "cumulative_pain": 3.21,
  "pain_history_cursor": 1847,
  "event_stream_cursor": 8291,
  "meaningful_event_count": 15,
  "last_score": 0.43
}
```

| Field | Type | Description |
|---|---|---|
| `last_computed_turn` | `int` | Turn number at last score computation |
| `cumulative_pain` | `float` | Running sum of all `severity` values processed so far |
| `pain_history_cursor` | `int` | Byte offset in `pain_history.jsonl` at end of last read |
| `event_stream_cursor` | `int` | Byte offset in `events.jsonl` at end of last read |
| `meaningful_event_count` | `int` | Running count of meaningful events processed so far |
| `last_score` | `float` | Most recently computed fitness score |

On first run (no state file exists), all cursors and accumulators start at zero.

The state file is written atomically after each score computation (temp-file rename — same pattern as IS-8 pain delivery queue).

If the state file is corrupt or unreadable, the fitness computer resets all state to zero and logs a warning. A reset produces a conservative (low) score from that point forward, not an abort.

#### IS-13.6 Running score computation

The running score is computed by the `fitness` package at the end of each turn, called from within `turn_engine.execute_turn()` after the `TURN_COMPLETE` event is written. This is a new implicit step between IS-6.3 step 17 (finalize TurnRecord) and step 18 (post-increment mortality check). [ASSUMED: The running score computation is not listed as a numbered step in IS-6.3 because it is an optional side-effect controlled by `fitness.compute_running_score`; the turn proceeds regardless of fitness computation success.]

**Computation procedure:**

1. If `fitness.enabled` is false or `fitness.compute_running_score` is false, skip and return.
2. Load `runtime/fitness/state.json`. If absent, initialize with all-zero state.
3. Read new records from `pain_history.jsonl` starting at `pain_history_cursor`. Accumulate `severity` sum into `cumulative_pain`. Update cursor.
4. Read new records from `runtime/event_stream/events.jsonl` starting at `event_stream_cursor`. Count new records whose `event_type` is in the meaningful events whitelist (IS-13.4). Add to `meaningful_event_count`. Update cursor.
5. Read current turn number from `runtime/memory/turn_state.json`.
6. Apply the formula (IS-13.3). Store result in `last_score`.
7. Write `runtime/fitness/current.json` (IS-13.8) atomically.
8. Write updated state back to `runtime/fitness/state.json` atomically.

If any step fails, log the error and return without aborting the turn. Fitness computation failure is never fatal. The turn has already completed successfully.

#### IS-13.7 Post-mortem score computation

The post-mortem score is computed by the `graveyard` during harvest (IS-12.3 step 5), after all artifact files have been copied to the output directory.

The post-mortem computation uses the **finalized copies** in the harvest output directory, not the live runtime files. This ensures the post-mortem score is self-consistent with the archived artifacts.

**Computation procedure:**

1. Read the unified `event_stream/events.jsonl` from the harvest output directory (already concatenated per IS-9.7 protocol).
2. Count all records whose `event_type` is in the meaningful events whitelist (IS-13.4).
3. Sum all `severity` values from `pain/pain_history.jsonl` in the harvest output directory.
4. Read final turn number from `memory/turn_state.json`.
5. Apply the formula (IS-13.3) using the full lifetime inputs.
6. Write `fitness/fitness_postmortem.json` to the harvest output directory (IS-13.8).

The post-mortem score is independent of the running score and the incremental state file. It is a clean recomputation over the full lifetime record.

#### IS-13.8 Output formats

**`runtime/fitness/current.json`** (running score, written by `fitness` package):

```json
{
  "instance_id": "lambertian-001",
  "computed_at_turn": 42,
  "computed_at": "2026-03-17T17:00:00.000Z",
  "score": 0.43,
  "components": {
    "lifespan_fraction": 0.0042,
    "engagement_fraction": 0.84,
    "normalized_pain": 0.321,
    "normalized_pain_effective": 0.321,
    "meaningful_event_count": 15,
    "expected_engagement": 10.5,
    "cumulative_pain": 3.21
  },
  "formula": "phase1_baseline"
}
```

**`fitness/fitness_postmortem.json`** (post-mortem score, written by `graveyard`):

```json
{
  "instance_id": "lambertian-001",
  "final_turn": 10000,
  "death_trigger": "max_age",
  "score": 0.74,
  "components": {
    "lifespan_fraction": 1.0,
    "engagement_fraction": 0.92,
    "normalized_pain": 1.34,
    "normalized_pain_effective": 1.34,
    "meaningful_event_count": 2300,
    "expected_engagement": 2500.0,
    "cumulative_pain": 13.4
  },
  "formula": "phase1_baseline"
}
```

The `normalized_pain_effective` field captures the value after applying `minimum_denominator` — it documents when the guard was engaged, which is useful for tuning `fitness.normalized_pain_baseline`.

#### IS-13.9 Pluggable registry architecture

The `fitness` package exposes a `FunctionRegistry` that maps function keys (strings) to `FitnessFunctionProtocol` implementations. The active function is selected by `fitness.active_function` from IS-1.

```python
class FitnessInput(Protocol):
    lifespan: int
    max_age: int
    meaningful_event_count: int
    expected_engagement: float
    cumulative_pain: float
    normalized_pain_baseline: float
    minimum_denominator: float

class FitnessScore(TypedDict):
    score: float
    components: dict[str, float]
    formula: str

class FitnessFunctionProtocol(Protocol):
    def compute(self, inputs: FitnessInput) -> FitnessScore: ...
```

The Phase 1 baseline is registered at startup as `"phase1_baseline"`. The registry raises a typed `UnknownFitnessFunctionError` if the configured key has no registration — this is a fatal startup error, not a runtime fallback.

[ASSUMED: The registry is populated at startup in `bootstrap` (IS-2.5) using a registration call, not a class-level decorator. Registration via decorator would make the registry implicitly global; injection via `bootstrap` keeps it explicit and testable.]

Phase 2/3 fitness functions are registered the same way. The Phase 1 codebase does not reference Phase 2/3 functions.

#### IS-13.10 Creator visibility mechanism

The creator observes fitness through:

1. **`runtime/fitness/current.json`** — written every turn (if `fitness.compute_running_score` is true). The creator can `tail -f` or periodically `cat` this file to watch the score evolve in real time.
2. **`fitness/fitness_postmortem.json`** in the graveyard harvest bundle — the definitive lifetime score.
3. **`creator_observability.live_running_fitness`** toggle (IS-1) — if this is true, the running score is also emitted to stdout by the `creator_observability` package (IS-2.5) so it appears in the container log stream. [ASSUMED: `creator_observability` logs the score as a structured JSON line to stdout, where it is captured by Docker and visible via `docker compose logs agent`.]

The instance does not receive the fitness score. It is not injected into the system prompt. It is not accessible via any MCP tool. The agent has no path to its own fitness value in Phase 1.

#### IS-13.11 Implementation note

- **IS-6 (The Turn)** calls the `fitness` package after step 17 (`TURN_COMPLETE` written). The running score computation is a post-turn side effect, not a turn step. Fitness failure must never fail the turn.
- **IS-12 (Graveyard Spec)** calls `fitness` at IS-12.3 step 5 for the post-mortem computation, passing the paths to the already-copied artifact files. IS-12 writes the resulting file; IS-13 owns the computation.
- **IS-8 (Pain Channel Spec)** owns `pain_history.jsonl`. IS-13 reads it using a byte-offset cursor. IS-13 must never write to pain files.
- **IS-9 (Event Stream Log)** owns `events.jsonl`. IS-13 reads it using a byte-offset cursor. IS-13 must never write to the event stream.

**Technical debt — file format coupling:** IS-13 reads `events.jsonl` and `pain_history.jsonl` directly as raw files using byte-offset cursors rather than through package interfaces owned by `event_log` and `pain_monitor`. This means IS-13 is coupled to the physical file formats of both packages. If either format changes — rotation naming, line encoding, schema evolution — IS-13 breaks silently. This is accepted for Phase 1 because the cursor-based incremental approach is straightforward and the formats are stable. **Phase 2 should address this:** the `event_log` package should expose a typed reader interface, and the `pain_monitor` package should expose a typed pain history reader, so IS-13 consumes abstractions rather than raw files. Do not extend the raw-file cursor pattern to additional data sources.

- **IS-1 (Universe Config)** holds all normalization knobs. IS-13 has no magic numbers — every constant is an IS-1 reference.
- **IS-2 (Project Layout)** lists `fitness` as a package in IS-2.5. No new package is introduced by IS-13.

---

