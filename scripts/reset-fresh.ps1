#!/usr/bin/env pwsh
# reset-fresh.ps1 — Lifecycle reset. Wipes agent runtime state and restarts.
#
# Preserves: lineage/ (cross-lifetime continuity), ollama weights, chroma data,
#            graveyard output archives.
# Clears:    agent-work (except lineage/), memory, pain queues, event stream,
#            fitness, self.
#
# Use before observing a clean lifetime.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

Write-Host "==> Stopping agent..." -ForegroundColor Cyan
docker compose stop agent

Write-Host "==> Clearing agent-work (preserving lineage/)..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_agent_work:/work alpine sh -c `
    "find /work -mindepth 1 -not -path '/work/lineage' -not -path '/work/lineage/*' -delete"

Write-Host "==> Restoring workspace scaffold..." -ForegroundColor Cyan
# Mirrors graveyard WorkspaceReset steps 2-3: recreate scaffold dirs and restore template files.
# The graveyard does this on natural death; reset-fresh.ps1 must do it on manual reset.
docker run --rm `
    -v lambertians_runtime_agent_work:/work `
    -v "${projectRoot}/config:/cfg:ro" `
    alpine sh -c "mkdir -p /work/journal /work/knowledge /work/observations /work/self /work/lineage && cp /cfg/workspace_scaffold/WORKSPACE.md /work/WORKSPACE.md && cp /cfg/workspace_scaffold/agent-work/self/constitution.md /work/self/constitution.md && echo 'Scaffold restored'"

Write-Host "==> Resetting memory (turn_state → 0)..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_memory:/mem alpine sh -c `
    'printf "{\"turn_number\": 0}" > /mem/turn_state.json && printf "{\"consecutive_reflection_count\": 0}" > /mem/reflection_state.json && rm -f /mem/working.json /mem/narrative.json'

Write-Host "==> Clearing pain queues..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_pain:/pain alpine sh -c `
    "rm -f /pain/death.json /pain/event_queue.jsonl /pain/event_queue_cursor.json /pain/pain_history.jsonl /pain/delivery_queue.json"

Write-Host "==> Clearing event stream..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_event_stream:/es alpine sh -c "rm -f /es/events.jsonl"

Write-Host "==> Clearing fitness..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_fitness:/fit alpine sh -c "rm -f /fit/current.json /fit/state.json"

Write-Host "==> Clearing self volume..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_self:/self alpine sh -c "find /self -mindepth 1 -delete"

Write-Host "==> Clearing ChromaDB episodic collection..." -ForegroundColor Cyan
# Mirrors graveyard step 8: delete-and-recreate so no prior-lifetime memory leaks through.
# Chroma stays running — only the agent was stopped.
docker run --rm --network lambertians_lambertian-core python:3.12-slim python3 -c "import chromadb; c = chromadb.HttpClient(host='chroma', port=8000); c.delete_collection('episodic'); c.get_or_create_collection('episodic', metadata={'hnsw:space': 'cosine'}); print('episodic collection cleared')"

Write-Host "==> Starting agent..." -ForegroundColor Cyan
docker compose up -d agent

Write-Host ""
Write-Host "Reset complete. Fresh lifetime starting." -ForegroundColor Green
