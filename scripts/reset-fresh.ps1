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

Write-Host "==> Resetting memory (turn_state → 0)..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_memory:/mem alpine sh -c `
    'printf "{\"turn_number\": 0}" > /mem/turn_state.json && rm -f /mem/working.json /mem/narrative.json'

Write-Host "==> Clearing pain queues..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_pain:/pain alpine sh -c `
    "rm -f /pain/death.json /pain/event_queue.jsonl /pain/event_queue_cursor.json /pain/pain_history.jsonl /pain/delivery_queue.json"

Write-Host "==> Clearing event stream..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_event_stream:/es alpine sh -c "rm -f /es/events.jsonl"

Write-Host "==> Clearing fitness..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_fitness:/fit alpine sh -c "rm -f /fit/current.json"

Write-Host "==> Clearing self volume..." -ForegroundColor Cyan
docker run --rm -v lambertians_runtime_self:/self alpine sh -c "find /self -mindepth 1 -delete"

Write-Host "==> Starting agent..." -ForegroundColor Cyan
docker compose up -d agent

Write-Host ""
Write-Host "Reset complete. Fresh lifetime starting." -ForegroundColor Green
