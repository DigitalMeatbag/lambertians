# Project Lambertian

**A constrained-agent testbed for studying model behavior, EOS design, and behavioral attractors.**

Project Lambertian is a locally-running AI agent architecture designed to surface how models behave under constrained, open-ended conditions. It has an inherited structure the agent cannot rewrite (**immutable instance configuration**), a mutable self that accumulates experience (**dynamic instance state**), environmental grounding that pushes back (**Ground**), a normative operating system (EOS) governing what actions are admissible, and a lineage mechanism for architectural change across generations.

It is not a chatbot. It is not an assistant. It is not trying to maximize anything.

The name refers to Lambertian reflectance — diffuse, non-specular, no harsh reflections. It receives from all directions and responds evenly.

---

## System Snapshot

- **What it is:** A constrained-agent testbed — no goals, no reward signal; behavior emerges from EOS rules and environmental feedback
- **Runtime:** Docker Compose services (agent, pain-monitor, eos-compliance, graveyard, ChromaDB), Ollama running qwen2.5:32b locally
- **Environment:** Filesystem (`runtime/`), HTTP, host telemetry — all accessed via MCP-mediated tooling
- **Behavior mechanism:** EOS (rule-based admissibility system) governs what actions are admissible; the Ground (external constraints and environment) pushes back against the agent's actions
- **What it does:** Runs continuous autonomous turns — reads and writes files, fetches URLs, updates working memory, accumulates episodic history
- **Current phase:** Phase 2 active
- **Model:** Configurable via `universe.toml` — currently running mistral-nemo:latest via Ollama

---

## Non-Goals

- Not a chatbot or assistant — there is no user to respond to
- Not a task optimizer — it has no goal to maximize
- Not reward-driven — there is no reward signal or RL training loop
- Not goal-directed planning — the EOS governs admissibility, not pursuit
- Not a benchmark target — behavioral quality is emergent, not scored against an external metric

---

## Why This Exists

Most AI evaluation puts models in structured tasks with known success criteria. That tells you how a model performs at the thing it's pointed at. It doesn't tell you much about how it behaves under open-ended conditions over time — what attractors it falls into, how it responds to environmental resistance, whether a normative framework produces meaningfully different behavior than an objective.

This project creates the conditions to observe that directly: a model running continuously under EOS constraints, with environmental feedback and mortality, leaving observable behavioral traces across lifetimes. The system is turning out to be quite good at uncovering stable behavioral attractors and characterizing how different EOS configurations shape agent behavior.

---

## Current Status

Phases 1 and 2 are complete. Phase 2 is active. A single Lambertian instance is running. See [`progress.md`](progress.md) for current implementation state and runtime observations.

The stack runs locally on Ollama (model is configurable via `universe.toml`), Docker Compose for the service topology, and ChromaDB for memory.

---

## Choose Your Path

**Start here if you want the *why*:**
→ [`manifesto.md`](manifesto.md) — Design rationale and conceptual framing. Why this architecture, what the EOS is doing, why constraints matter, what the failure modes are trying to prevent.

**Start here if you want to understand how it works:**
→ [`technical.md`](technical.md) — The engineering overview. Architecture, layers, EOS in practical terms, pain/mortality, memory model, technical stack, failure modes. Written for engineers who want to understand the system without reading the full spec.

**Start here if you're building it:**
→ [`implementation_spec.md`](implementation_spec.md) — The formal IS-level spec. IS-1 through IS-13. Universe Config, service topology, the turn loop, pain channels, compliance inspector, graveyard, fitness function. This is the contract.

**Start here to see what's done:**
→ [`progress.md`](progress.md) — Current implementation status, completed decisions, runtime observations, open questions, next steps. Updated as the project moves.
