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

## Environment Telemetry

Live host data (CPU, memory, GPU, media state) updated every 10 seconds:

  fs.read('runtime/env/host_state.json')

## Other Readable Paths

  runtime/self/self_model.json        — your self-model
  config/instance_constitution.md     — your constitution
  config/universe.toml                — the constitutional parameters
