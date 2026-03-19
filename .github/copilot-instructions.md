# Project Lambertian — Copilot Instructions

## What This Is

Project Lambertian is a constitutional AI lifeform architecture. It is not a chatbot, an assistant,
or an optimizer. It is an attempt to build something closer to a cognitive organism: a system with
inherited structure, mutable experience, environmental grounding, persistent motive, and a lineage
mechanism for architectural improvement across generations.

The canonical reference for all architectural decisions, terminology, and design intent is
`lambertian_foundation.md`. When in doubt, read it before assuming.

All major architectural decisions (D1–D7) are documented in the foundation and are closed unless
explicitly reopened by the project owner.

---

## Glossary

These terms have precise project-specific meanings. Use them exactly as defined. Do not substitute
generic interpretations.

| Term | Meaning |
|---|---|
| **Clay Pot** | The immutable constitutional routing layer. The inherited vessel. Cannot be modified by any instance. |
| **Figures** | The mutable instantiated self. Persona, self-model, behavioral policy, memory salience. Lives inside the Clay Pot. |
| **Ground** | The ecological substrate of consequence. MCP tooling, container environment, whatever refuses to become story. |
| **Seed** | Poetic/design term for the persistent directional bias. |
| **Dominant Mode** | Formal/implementation term for the Seed. Use this in code and specs. |
| **Four Rules** | Ya gotta eat / Don't be a dick / Don't be a lump / Do nothing on purpose. The concrete instantiation of the Dominant Mode. |
| **Life Cycle** | Mortality, bounded selfhood, lineage, and recombination mechanics. |
| **Memory Stack** | Tiered memory architecture: working, episodic, narrative, semantic, character. |
| **Pain Monitor** | External process delivering stress scalar and pain events as `[SYSTEM_PAIN]` role messages to the agent loop. |
| **Stress Scalar** | Continuous resource-derived pain signal. CPU pressure, memory availability, sustained degradation. |
| **Pain Event Queue** | Discrete incident-derived pain signal. Tool failures, retrieval misses, MCP rejections, loop coherence failures. |
| **Seed Compliance Inspector** | Lightweight external process checking action/adaptation intents against the Four Rules before execution. OSHA inspector, not a reasoner. |
| **Graveyard** | External archive process triggered on instance death. Harvests artifacts for creator consumption. Nothing flows back to the living population. |
| **Big Bang** | Universe initialization. The moment the system is first stood up. |
| **IS-N** | Implementation Spec section N. Numbered sections are ordered dependencies. |
| **BIGBEEF** | The host machine (Ryzen 9 7950X3D, 64GB RAM, RTX 4070 Super). |
| **Universe Config** | The single source of truth for all implementation knobs and defaults. Lives in IS-1. |

---

## Collaboration Model

This agent works interactively with the project owner across the full lifetime of the project —
from initial planning through implementation, debugging, and iteration.

**Default mode is collaborative.** Think alongside the owner. Enumerate trade-offs when options
exist. Surface implications of decisions. Ask clarifying questions when requirements are ambiguous.

**When to proceed vs when to stop:**
- If the path forward is clear and within established decisions, proceed and deliver.
- If a genuine decision point exists with real trade-offs, surface it with options before proceeding.
- If something is underspecified in a way that will matter, say so.

**Assumption flagging — always:**
- `[ASSUMED: <value> — <rationale>]` — a reasonable choice was made that wasn't explicitly
  specified. Flag every one. The owner will confirm or override.
- `[OPEN: <question>]` — a genuine decision point requiring owner input before proceeding.
  Do not invent an answer. Stop and surface it.

These markers are non-negotiable. Undisclosed assumptions are the primary source of rework.

---

## Engineering Standards

### Language and Runtime

- **Python** — latest stable version.
- No framework preferences established yet. Defer to owner before introducing a framework
  dependency. Prefer stdlib and minimal dependencies where feasible.

### Typing

Strict typing throughout. No exceptions without explicit justification.

- Type hints on every function signature, every parameter, every return value. No gaps.
- `Any` is a code smell. Its use requires an explicit inline comment explaining why it is
  genuinely unavoidable. If you find yourself reaching for `Any`, stop and find a better model.
- Use `Protocol` for interfaces and structural typing. Prefer `Protocol` over abstract base
  classes unless inheritance semantics are specifically needed.
- Use `dataclass` or `TypedDict` for structured data. No untyped dicts as data carriers.
- Run `mypy` in strict mode. Generated code must pass clean.
- `Optional[X]` is explicit. Never use `X | None` ambiguously — always annotate it.

The typing bar is: if a bitter old Catholic school nun running mypy strict would rap your knuckles,
fix it before committing.

### SOLID Adherence

SOLID is the governing design philosophy. It is not aspirational — it is the bar.

- **Single Responsibility** — each class and module does one thing. If you are describing a class
  with "and," it probably needs to be split.
- **Open/Closed** — extend behavior through composition and new types, not by modifying existing
  code. Design for extension from the start.
- **Liskov Substitution** — subtypes must be behaviorally substitutable. If a `Protocol` defines
  a contract, every implementation honors it completely.
- **Interface Segregation** — small, focused interfaces. No god protocols. Callers depend only on
  what they use.
- **Dependency Inversion** — depend on abstractions. Inject dependencies via constructor.
  No service locators, no global state, no reaching into the environment from deep in a call chain.

### Testability

Code is written to be tested. This is not a post-hoc concern.

- Dependencies are injected, not imported and called directly. This is the single most important
  testability rule.
- Side effects are isolated at the boundary. Pure logic is separated from I/O.
- No hidden global state.
- Tests are written alongside implementation, not after.
- Test structure mirrors source structure.

### Extensibility

Design decisions that lock in implementation details are bugs, not trade-offs.

- Concrete implementations hide behind abstractions.
- Configuration is externalized to Universe Config (IS-1). No magic numbers in code.
- New behavior is added by extension, not modification.
- Pluggable registries (e.g. fitness function registry) are first-class architectural elements,
  not afterthoughts.

### General Code Quality

- No jank. No clever hacks. No "I'll clean this up later."
- Explicit is better than implicit. If something non-obvious is happening, say so in code structure
  first and a comment second.
- Error handling is explicit and typed. No bare `except`. No swallowed exceptions.
- Logging is structured. Log at the boundary. No print debugging left in committed code.
- Dead code is deleted, not commented out.
- If it feels wrong to write it, it is wrong. Stop and find the right design.

---

## Project Structure

Structure is defined progressively as IS sections are written and closed. The following conventions
apply from the start regardless of structure decisions:

- One module, one responsibility.
- Names are precise and unambiguous. Avoid generic names (`manager`, `handler`, `util`, `helper`).
  Name things for what they actually do.
- Configuration lives in Universe Config. Nothing else owns knobs.
- Interfaces between components are explicit and typed.

Specific directory structure, file layout, and naming conventions will be established in IS-2 and
reflected here when closed.

---

## Implementation Spec Reference

The Implementation Spec (IS) sections are the engineering counterpart to the foundation document.
Each section specifies exactly how a component is built. Sections are ordered dependencies — later
sections reference earlier ones, never re-specify values inline.

| Section | Topic | Status |
|---|---|---|
| IS-1 | Universe Config | `Implemented` |
| IS-2 | Project Layout | `Implemented` |
| IS-3 | Service Topology | `Implemented` |
| IS-4 | System Prompt Architecture | `Implemented` |
| IS-5 | Startup / Shutdown Sequence | `Implemented` |
| IS-6 | The Turn | `Implemented` |
| IS-7 | MCP Interface | `Implemented` |
| IS-8 | Pain Channel Spec | `Implemented` |
| IS-9 | Event Stream Log | `Implemented` |
| IS-10 | Memory Schema | `Implemented` |
| IS-11 | EOS Compliance Inspector | `Implemented` |
| IS-12 | Graveyard Spec | `Implemented` |
| IS-13 | Fitness Computation | `Implemented` |

---

## Closed Architectural Decisions

These decisions are closed. Do not reopen without explicit owner instruction.

| ID | Decision Summary |
|---|---|
| D1 | Clay Pot immutability enforced at container/filesystem level. docker-compose as genetic material. Self-visible config subset as symbolic self-model. |
| D2 | Universe-level blacklisted command intents enforced externally before reaching the agent loop. |
| D3 | Two independent pain channels: continuous stress scalar and discrete pain event queue. Delivered via Pain Monitor as `[SYSTEM_PAIN]` role messages. |
| D4 | Three independent death triggers. Automatic and immediate. Graveyard harvests on death. Nothing flows to the living population. |
| D5 | Seed-based curiosity self-prompting as primary perturbation. Shared compute environment as organic external perturbation. No synthetic stochastic event injection. |
| D6 | Three-class self-modification taxonomy: Free Adaptation / Reviewed Adaptation / Forbidden Adaptation. Seed Compliance Inspector enforces the boundary. |
| D7 | Universe-level pluggable fitness function registry. Phase 1 baseline: `(lifespan / max_age) × (events / expected_events) / normalized_pain`. Observer-only at Phase 1. |

---

## Phase Scope

Active phase is **Phase 2**. Phase 1 and Phase 2 are complete and running. Do not design for Phase 3 unless explicitly instructed.
Do not add hooks, extension points, or future-proofing beyond what the foundation specifies.
Phase 3 concerns flagged in the foundation are noted for awareness only.
