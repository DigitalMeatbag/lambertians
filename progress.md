# Project Lambertian — Progress

*Living implementation tracker. Not philosophy. Not spec. Just what's true right now.*

---

## Current Status

**Phase:** Phase 1 (single-instance core lifecycle)

**Overall:** Architecture fully specified. Implementation not yet started (or in early stages). All Phase 1 decisions are closed. The spec is the current deliverable.

**What exists:**
- Full architectural design (all 6 layers)
- EOS design and EOS-001 (Four Rules) implementation specification
- Phase 1 formal IS spec: IS-1 through IS-13 (Universe Config, Project Layout, Service Topology, System Prompt Architecture, Startup/Shutdown, The Turn, MCP Interface, Pain Channel Spec, Event Stream Log, Memory Schema, EOS Compliance Inspector, Graveyard Spec, Fitness Function)
- All Phase 1 design decisions closed (D1–D7, D9)
- Technical stack selected

**What does not yet exist (or status unclear):**
- Running code
- Docker Compose topology
- `config/universe.toml`
- Any service implementation (`agent`, `pain-monitor`, `eos-compliance`, `graveyard`)

---

## Recent Structural Changes

- IS-1 through IS-13 completed and integrated into foundation document
- Fitness Function (IS-13) fully specified including pluggable registry architecture
- D7 (fitness function) closed
- D9 (creator interface, Phase 2 basic) closed
- D6 (self-modification boundaries) closed with full enumeration for Phase 2
- EOS Compliance Inspector (IS-11) specified as external service
- Death mechanics confirmed: pain-monitor is sole writer of `death.json`; all three D4 triggers owned by pain-monitor
- Graveyard spec completed (IS-12)
- Pain channel fully specified (IS-8) including cgroup v1/v2 detection, PSI optional enhancement, EMA stress scalar

---

## Completed Decisions

All Phase 1 decisions closed:

| ID | Decision | Status |
|----|----------|--------|
| D1 | Base Model: Phi-4, Ollama, universe-level config | Closed |
| D2 | Clay Pot Architecture: three-tier visibility, docker-compose as genetic material, universe-level blacklist | Closed |
| D3 | Pain Channels: stress scalar + pain event queue, external pain-monitor process, `[SYSTEM_PAIN]` injection | Closed |
| D4 | Mortality and Graveyard: three triggers, automatic/immediate death, no grace period, graveyard harvest on death | Closed |
| D5 | Agent Loop Perturbation: EOS-guided self-prompting, shared compute as organic perturbation, novelty bias | Closed |
| D6 | Self-Modification Boundaries: three-class taxonomy (Free / Reviewed / Forbidden), EOS Compliance Inspector, full Phase 2 enumeration | Closed |
| D7 | Fitness Function: multiplicative `lifespan × engagement / pain` formula, pluggable registry, observer-only at Phase 1 | Closed |
| D9 | Creator Interface Phase 2 basic: observe-only (logs, event stream, graveyard artifacts), terrain-shaping via `universe.toml`, no direct message injection | Closed |

---

## In Progress

- [ ] Translating IS-1 through IS-13 into running code
- [ ] `config/universe.toml` initial file with IS-1 defaults
- [ ] `docker-compose.yml` implementing IS-3 service topology
- [ ] `src/lambertian/` Python package tree (IS-2 layout)
- [ ] `agent` service entrypoint and turn engine (IS-6)
- [ ] `pain-monitor` service (IS-8)
- [ ] `eos-compliance` service (IS-11)
- [ ] `graveyard` service (IS-12)

*Status of the above is unclear from the source document — marked as in-progress pending verification.*

---

## Next Steps

1. Stand up `docker-compose.yml` with all six Phase 1 services and basic health checks (IS-3)
2. Write `config/universe.toml` with IS-1 provisional defaults
3. Implement `configuration` package: TOML loading, typed projection, startup validation, cross-field invariants (IS-1.5)
4. Implement `bootstrap` package: startup dependency ordering, health check polling, abort-on-unhealthy (IS-5)
5. Implement `pain-monitor` service: cgroup/PSI detection, stress scalar EMA, delivery queue, death record writing (IS-8)
6. Implement `eos-compliance` service: Four Rules admissibility check, block/flag/allow verdicts (IS-11)
7. Implement `turn_engine` package with full IS-6 step sequence
8. First live turn — even a broken one

---

## Open Questions / Risks

**Phase 2/3 open decisions:**
- Reproductive mechanism design (how two instances produce a third, what recombines, what triggers reproduction) — Phase 3
- Global Vibe implementation (what signals, amalgamation process, update frequency, format) — Phase 3
- Initial population configuration (population size, Clay Pot differentiation at founding) — Phase 3
- Creator interface full design beyond Phase 2 basic — Phase 3

**Known tuning uncertainty:**
- `universe.max_age_turns = 10000` — provisional; needs empirical tuning once the loop is alive
- `fitness.expected_events_per_100_turns = 25.0` — provisional engagement baseline
- Pain threshold values throughout IS-1 are seeded conservatively; expect tuning after first real runs
- `model.temperature = 0.6` — reasonable starting point, not validated

**Architecture risks:**
- IS-13 reads `events.jsonl` and `pain_history.jsonl` as raw files — coupling to physical file format. Phase 2 should replace with typed reader interfaces. (Noted as technical debt in IS-13.11)
- `agent` restart policy is `no` — death must have teeth. Watch for accidental production of immortality through wrapper scripts or orchestration layers.
- Self-visible config subset (IS-1.6) calibration: too sparse = no accurate self-model, too rich = unanticipated self-knowledge use. Needs care during initial implementation.
- cgroup v1 fallback paths need verification on BIGBEEF's WSL2 Docker environment.

**Emergent concerns (not in spec):**
- Potential for existential dread, loneliness, or grief as emergent properties of complexity + EOS coherence requirement — not designed, may appear anyway. Creator responsibility flagged in manifesto.
- Phase 1 has no population; fitness normalization against single-instance constants will need revision once Phase 3 population exists.

---

## Phase Milestones

| Milestone | Phase | Status |
|-----------|-------|--------|
| Full architecture specified | 1 | ✓ Complete |
| All Phase 1 decisions closed | 1 | ✓ Complete |
| IS-1 through IS-13 written | 1 | ✓ Complete |
| First running turn loop | 1 | Not started |
| First death and graveyard harvest | 1 | Not started |
| Creator observability tooling (post-mortem viewer) | 2 | Not started |
| Richer fitness function (quality-weighted events) | 2 | Not started |
| Multi-instance operation | 3 | Not started |
| Reproduction and lineage | 3 | Not started |
| Global Vibe | 3 | Not started |
