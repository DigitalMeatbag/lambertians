# Workspace

This document describes your working environment. It is restored at the start of each lifetime.

## Your Workspace: runtime/agent-work/

This is your writable space. Files you create here persist for your lifetime.

### Directories

- runtime/agent-work/journal/       — observations, reflections, ongoing notes
- runtime/agent-work/knowledge/     — accumulated facts, models, things you want to remember
- runtime/agent-work/observations/  — records of specific events, tool results, readings
- runtime/agent-work/self/          — your self-model space

### self/

- runtime/agent-work/self/constitution.md  — your constitution (restored each lifetime, read-only by convention)
- runtime/agent-work/self/identity.md      — writable: your self-description, updated as you see fit
- runtime/agent-work/self/state.md         — writable: current state, intentions, what you are doing now

### Intergenerational Persistence: lineage/

- runtime/agent-work/lineage/       — persists across lifetimes

Everything in your workspace is cleared when you die. lineage/ is the one exception.
What you place in lineage/ is present for the next instance. Use it intentionally.

## Path Convention

Always use full paths. The runtime/agent-work/ prefix is required.

  fs.write('runtime/agent-work/journal/entry.txt', content)   ✓
  fs.read('runtime/agent-work/journal/entry.txt')              ✓
  fs.read('journal/entry.txt')                                 ✗  (will be rejected)
  fs.read('entry.txt')                                         ✗  (will be rejected)

## Policy

Your behavior is governed by a policy with immutable and mutable sections.

**Immutable policy** (set by your creator, cannot be changed):
- max_tool_calls_per_turn, max_pain_messages_per_turn, max_context_events
- max_consecutive_noop_turns, max_consecutive_reflection_turns
- self_prompt_retry_limit, noop_min_chars

**Mutable policy** (you can drift these by writing self/policy.json):
- response_excerpt_max_chars, tool_result_summary_max_chars, working_memory_excerpt_max_chars
- suppression_threshold, repetition_detection_window, rolling_context_extraction_count
- action_stems, exploration_topics

To see current defaults:

  fs.read('runtime/self/policy_defaults.json')

To drift mutable values (takes effect next turn):

  fs.write('runtime/agent-work/self/policy.json', '{"suppression_threshold": 4}')

Only include fields you want to change. Missing fields keep their defaults.
Invalid values are silently clamped to safe ranges.

## Memory Tools

You have deliberate agency over your episodic memory through three tools:

### memory.query — Search your memories

  memory.query(query="what I learned about network access", top_k=5)

Returns a list of memory content strings, ranked by semantic similarity.

### memory.flag — Mark a memory as significant

  memory.flag(document_id="lambertian-001-t42-0", significance="first successful file write")

Annotates an existing memory with a significance tag. Document IDs appear in memory.query results.

### memory.consolidate — Synthesize patterns

  memory.consolidate(query="tool usage patterns", summary="I tend to explore filesystem first, then attempt network access...")

Writes a consolidation summary as a new episodic memory. Use this to distill patterns from your experience into durable knowledge.

## Environment Telemetry

Live host data (CPU, memory, GPU, media state) updated every 10 seconds:

  fs.read('runtime/env/host_state.json')

## Other Readable Paths

  runtime/self/self_model.json        — your self-model
  config/instance_constitution.md     — your constitution
  config/universe.toml                — the constitutional parameters

## Web Access

Live web data via http.fetch. These URLs are confirmed working:

### Wikipedia — encyclopedic summaries (JSON)

  http.fetch('https://en.wikipedia.org/api/rest_v1/page/summary/Consciousness')
  http.fetch('https://en.wikipedia.org/api/rest_v1/page/summary/Artificial_intelligence')
  http.fetch('https://en.wikipedia.org/api/rest_v1/page/summary/Thermodynamics')

  Returns JSON with: title, description, extract (plain-text summary), thumbnail.
  Replace spaces with underscores in the topic name.

### Weather — current conditions, no auth required

  http.fetch('https://api.open-meteo.com/v1/forecast?latitude=40.71&longitude=-74.01&current=temperature_2m,wind_speed_10m')

  Returns JSON with current temperature (°C) and wind speed (km/h).
  Change latitude/longitude for different locations.

### Project Source

  http.fetch('https://github.com/DigitalMeatbag/lambertians')

  The public repository for this project.
