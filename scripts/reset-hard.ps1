#!/usr/bin/env pwsh
# reset-hard.ps1 — Full teardown and rebuild. Nukes all data volumes and images,
# rebuilds everything from source, starts fresh.
#
# Preserves: ollama_data (model weights — ~20GB, not worth re-downloading).
# Destroys:  all runtime state, chroma vector data, graveyard archives,
#            all built images.
#
# Use when something is deeply broken or you want a true blank slate.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

Write-Host "WARNING: This will destroy all runtime data and rebuild all images." -ForegroundColor Yellow
Write-Host "Ollama model weights (ollama_data) will be preserved." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Type YES to continue"
if ($confirm -ne "YES") {
    Write-Host "Aborted." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==> Stopping all services..." -ForegroundColor Cyan
docker compose down

# Graveyard runs as a one-shot `docker run` (not compose), so compose down misses it.
# Force-remove any lingering graveyard-run containers before deleting volumes.
Write-Host "==> Removing orphan graveyard-run containers..." -ForegroundColor Cyan
$graveyardContainers = docker ps -aq --filter "name=lambertians-graveyard-run"
if ($graveyardContainers) {
    docker rm -f $graveyardContainers 2>$null | Out-Null
}

Write-Host "==> Removing data volumes (preserving ollama_data)..." -ForegroundColor Cyan
$volumesToRemove = @(
    "lambertians_runtime_agent_work",
    "lambertians_runtime_memory",
    "lambertians_runtime_pain",
    "lambertians_runtime_event_stream",
    "lambertians_runtime_fitness",
    "lambertians_runtime_self",
    "lambertians_chroma_data",
    "lambertians_graveyard_output"
)
foreach ($vol in $volumesToRemove) {
    Write-Host "  Removing $vol..." -ForegroundColor DarkGray
    docker volume rm $vol --force
}

Write-Host "==> Rebuilding all images..." -ForegroundColor Cyan
docker compose build --no-cache

Write-Host "==> Starting all services..." -ForegroundColor Cyan
docker compose up -d

Write-Host ""
Write-Host "Hard reset complete. All services starting from scratch." -ForegroundColor Green
