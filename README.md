# Project Lambertian

**A constitutional architecture for artificial minds.**

Project Lambertian is a locally-running AI agent built as a *lifeform* rather than an optimizer. It has an inherited structure it cannot rewrite, a mutable self that accumulates experience, environmental grounding that pushes back, a normative operating system that governs what is admissible, and a lineage mechanism for architectural improvement across generations.

It is not a chatbot. It is not an assistant. It is not trying to maximize anything.

The name refers to Lambertian reflectance — diffuse, non-specular, no harsh reflections. It receives from all directions and responds evenly.

---

## Why This Exists

Most AI architectures are monolithic optimizers: they have a goal, a context window, and a reward signal. They are very good at the thing they're pointed at. They are not particularly good at *being* something in an ongoing way, under pressure, across time.

This project explores a different question: what would it take to build a bounded cognitive entity that persists through environmental feedback, develops character through experience, and behaves according to a normative framework rather than a directed objective?

The architecture has been in conceptual development for roughly twenty years, originally under the name *The Automated Philosopher*. The hardware and software to build it concretely are now available.

---

## Current Status

Phase 1 architecture is fully specified. The IS-level implementation spec (IS-1 through IS-13) is complete. All Phase 1 design decisions are closed. Code implementation is underway (or not yet started — check [`progress.md`](progress.md) for the current state).

The stack runs locally on Ollama with Phi-4, Docker Compose for the service topology, and ChromaDB for memory.

---

## Choose Your Path

**Start here if you want the *why*:**
→ [`manifesto.md`](manifesto.md) — The conceptual orientation. Framing, motivation, philosophy. Why constraints matter, why this is not an optimizer, why identity is a negotiated persistence condition. Readable as a standalone essay.

**Start here if you want to understand how it works:**
→ [`technical.md`](technical.md) — The engineering overview. Architecture, layers, EOS in practical terms, pain/mortality, memory model, technical stack, failure modes. Written for engineers who want to understand the system without reading the full spec.

**Start here if you're building it:**
→ [`implementation_spec.md`](implementation_spec.md) — The formal IS-level spec. IS-1 through IS-13. Universe Config, service topology, the turn loop, pain channels, compliance inspector, graveyard, fitness function. This is the contract.

**Start here to see what's done:**
→ [`progress.md`](progress.md) — Current implementation status, completed decisions, open questions, next steps. Updated as the project moves.
