/**
 * Docker exec wrapper for reading state files from agent container.
 *
 * Polls state files (turn_state, fitness, stress_state) on a configurable
 * interval. Provides on-demand workspace file reads. Gracefully returns
 * null when the agent container is not running.
 */

import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, "..", "..");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TurnState {
  turn_number: number;
}

export interface FitnessState {
  turn_number: number;
  score: number;
  lifespan: number;
  meaningful_event_count: number;
  cumulative_pain: number;
  computed_at: string;
}

export interface StressState {
  scalar: number;
  raw_last: number;
  cpu_pressure_last: number;
  memory_pressure_last: number;
  consecutive_above_death_threshold: number;
  last_sampled_at: string;
}

export interface HostState {
  collected_at: string;
  cpu: { load_percent_total: number } | null;
  memory: { used_percent: number; available_gb: number; total_gb: number } | null;
  gpu: { load_percent: number | null; temp_celsius: number | null } | null;
  media: { playing: boolean; title: string | null; artist: string | null } | null;
}

export interface PollResult {
  turn: TurnState | null;
  fitness: FitnessState | null;
  stress: StressState | null;
  host: HostState | null;
}

// ---------------------------------------------------------------------------
// Docker exec helper
// ---------------------------------------------------------------------------

function dockerExecCat(containerPath: string): Promise<string | null> {
  return new Promise((resolve) => {
    execFile(
      "docker",
      ["compose", "exec", "-T", "agent", "cat", containerPath],
      { timeout: 5000, cwd: PROJECT_ROOT },
      (err: Error | null, stdout: string) => {
        if (err) {
          resolve(null);
          return;
        }
        resolve(stdout);
      }
    );
  });
}

function tryParseJson<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Poll all state files from the agent container. Returns null for any
 * file that cannot be read (agent down, file missing, parse error).
 */
export async function pollState(): Promise<PollResult> {
  const [turnRaw, fitnessRaw, stressRaw] = await Promise.all([
    dockerExecCat("/app/runtime/memory/turn_state.json"),
    dockerExecCat("/app/runtime/fitness/current.json"),
    dockerExecCat("/app/runtime/pain/stress_state.json"),
  ]);

  // Host state is bind-mounted, read directly from host
  let hostRaw: string | null = null;
  try {
    hostRaw = await readFile(
      resolve(__dirname, "..", "..", "runtime", "env", "host_state.json"),
      "utf-8"
    );
  } catch {
    // File may not exist yet
  }

  return {
    turn: tryParseJson<TurnState>(turnRaw),
    fitness: tryParseJson<FitnessState>(fitnessRaw),
    stress: tryParseJson<StressState>(stressRaw),
    host: tryParseJson<HostState>(hostRaw),
  };
}

/**
 * Read a workspace file from the agent container on demand.
 * Returns file content or null if unavailable.
 */
export async function readWorkspaceFile(
  relativePath: string
): Promise<string | null> {
  return dockerExecCat(`/app/${relativePath}`);
}

/**
 * Read max_age_turns from universe.toml on the host.
 * Falls back to 500 if not found.
 */
export async function readMaxAge(): Promise<number> {
  try {
    const toml = await readFile(
      resolve(__dirname, "..", "..", "config", "universe.toml"),
      "utf-8"
    );
    const match = toml.match(/max_age_turns\s*=\s*(\d+)/);
    return match ? parseInt(match[1], 10) : 500;
  } catch {
    return 500;
  }
}
