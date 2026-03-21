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

export interface SelfModelState {
  instance_id: string;
  model_name: string;
}

export interface PollResult {
  turn: TurnState | null;
  fitness: FitnessState | null;
  stress: StressState | null;
  host: HostState | null;
  selfModel: SelfModelState | null;
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
 *
 * Bind-mounted files (host_state.json, self_model.json) are read directly
 * from the host filesystem. Container state files use docker exec.
 */
export async function pollState(): Promise<PollResult> {
  const [turnRaw, fitnessRaw, stressRaw] = await Promise.all([
    dockerExecCat("/app/runtime/memory/turn_state.json"),
    dockerExecCat("/app/runtime/fitness/current.json"),
    dockerExecCat("/app/runtime/pain/stress_state.json"),
  ]);

  let hostRaw: string | null = null;
  let selfModelRaw: string | null = null;
  try {
    [hostRaw, selfModelRaw] = await Promise.all([
      readFile(resolve(__dirname, "..", "..", "runtime", "env", "host_state.json"), "utf-8").catch(() => null),
      readFile(resolve(__dirname, "..", "..", "runtime", "self", "self_model.json"), "utf-8").catch(() => null),
    ]);
  } catch {
    // Files may not exist yet
  }

  return {
    turn: tryParseJson<TurnState>(turnRaw),
    fitness: tryParseJson<FitnessState>(fitnessRaw),
    stress: tryParseJson<StressState>(stressRaw),
    host: tryParseJson<HostState>(hostRaw),
    selfModel: tryParseJson<SelfModelState>(selfModelRaw),
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

export interface InstanceConfig {
  instanceId: string;
  modelName: string;
}

/**
 * Read instance identity from runtime/self/self_model.json (written by the
 * running container at bootstrap). Falls back to universe.toml if the file
 * doesn't exist yet. The toml fallback resolves the active profile's name
 * field the same way the Python config loader does.
 */
export async function readInstanceConfig(): Promise<InstanceConfig> {
  // Prefer self_model.json — written by the actual running container, so it
  // reflects the live model regardless of which branch we're on.
  try {
    const raw = await readFile(
      resolve(__dirname, "..", "..", "runtime", "self", "self_model.json"),
      "utf-8"
    );
    const data = tryParseJson<SelfModelState>(raw);
    if (data?.instance_id && data?.model_name) {
      return { instanceId: data.instance_id, modelName: data.model_name };
    }
  } catch {
    // File not present yet; fall through to toml
  }

  // Fall back to universe.toml. Resolve the active profile's name field the
  // same way the Python config loader does: active_profile is the key into
  // [model.profiles], and name is a field inside that profile entry.
  try {
    const toml = await readFile(
      resolve(__dirname, "..", "..", "config", "universe.toml"),
      "utf-8"
    );
    const idMatch = toml.match(/instance_id\s*=\s*"([^"]+)"/);
    const activeProfileMatch = toml.match(/active_profile\s*=\s*"([^"]+)"/);

    let modelName = "unknown";
    if (activeProfileMatch) {
      const key = activeProfileMatch[1];
      const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const nameMatch = toml.match(
        new RegExp(`\\[model\\.profiles\\.\"${escapedKey}\"\\][\\s\\S]*?\\bname\\s*=\\s*"([^"]+)"`)
      );
      modelName = nameMatch ? nameMatch[1] : key;
    }

    return {
      instanceId: idMatch ? idMatch[1] : "unknown",
      modelName,
    };
  } catch {
    return { instanceId: "unknown", modelName: "unknown" };
  }
}
