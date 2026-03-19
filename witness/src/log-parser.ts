/**
 * Line-oriented parser for agent container log output.
 *
 * Parses `docker compose logs -f agent` lines into structured events.
 * Fault-tolerant: unrecognized lines are silently dropped.
 */

// ---------------------------------------------------------------------------
// Event types emitted by the parser
// ---------------------------------------------------------------------------

export type ToolOutcome = "ok" | "fail" | "blocked";

export interface ToolCall {
  tool: string;
  args: string;
}

export interface TurnEvent {
  kind: "turn";
  turn: number;
  role: string;
  text: string | null;
  tools: ToolCall[];
}

export interface SuppressionEvent {
  kind: "suppression";
  turn: number;
  suppressedTools: string[];
}

export interface ShimEvent {
  kind: "shim";
  shimType: "alias/read" | "alias/list" | "virtual/read";
  originalPath: string;
  target: string;
}

export interface DeathEvent {
  kind: "death";
  turn: number;
}

export interface ToolResultEvent {
  kind: "tool_result";
  turn: number;
  tool: string;
  path: string;
  outcome: ToolOutcome;
  chars?: number;
}

export type LogEvent =
  | TurnEvent
  | SuppressionEvent
  | ShimEvent
  | DeathEvent
  | ToolResultEvent;

// ---------------------------------------------------------------------------
// Regex patterns
// ---------------------------------------------------------------------------

// [t42][SELF_PROMPT] text  →tools: fs.list('runtime/')
const TURN_RE =
  /\[t(\d+)\]\[([^\]]+)\]\s*(.*?)(?:\s+→tools:\s+(.+))?$/;

// [t42] tool suppression active — suppressed: fs.list, fs.read
const SUPPRESSION_RE =
  /\[t(\d+)\] tool suppression active\s*(?:—|--)\s*suppressed:\s*(.+)$/;

// Semantic shim (alias/read): 'WORKSPACE.md' → 'runtime/agent-work/WORKSPACE.md'
const SHIM_RE =
  /Semantic shim \(([^)]+)\):\s*'([^']+)'\s*(?:→|->)\s*(?:generator\s*)?'([^']+)'/;

// DEATH_TRIGGER or death-related log lines
const DEATH_RE = /\[t(\d+)\].*(?:DEATH_TRIGGER|death|max_age)/i;

// Tool call format: fs.write('runtime/agent-work/test.txt', 42chars)
const TOOL_CALL_RE = /(\w+\.\w+)\('([^']*)'(?:,\s*(\d+)chars)?\)/g;

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

/**
 * Parse a single log line. Returns null if the line is unrecognized.
 *
 * The docker compose logs prefix (`agent-1  | 2026-...`) is stripped before
 * pattern matching.
 */
export function parseLine(raw: string): LogEvent | null {
  // Strip docker compose log prefix: "agent-1  | 2026-03-19 18:27:16,869 INFO ... — "
  const pipeIdx = raw.indexOf(" | ");
  const line = pipeIdx >= 0 ? raw.slice(pipeIdx + 3) : raw;

  // Strip timestamp + level + logger prefix to get the message
  // Format: "2026-03-19 18:27:16,869 INFO lambertian.xxx.yyy — MESSAGE"
  const dashIdx = line.indexOf(" — ");
  const emDashIdx = line.indexOf(" \u2014 ");
  const msgStart = Math.max(dashIdx, emDashIdx);
  const msg = msgStart >= 0 ? line.slice(msgStart + 3) : line;

  // Try suppression first (before turn, since suppression lines also have [tN])
  const suppMatch = msg.match(SUPPRESSION_RE);
  if (suppMatch) {
    return {
      kind: "suppression",
      turn: parseInt(suppMatch[1], 10),
      suppressedTools: suppMatch[2].split(",").map((s) => s.trim()),
    };
  }

  // Turn event
  const turnMatch = msg.match(TURN_RE);
  if (turnMatch) {
    const tools: ToolCall[] = [];
    if (turnMatch[4]) {
      for (const m of turnMatch[4].matchAll(TOOL_CALL_RE)) {
        tools.push({ tool: m[1], args: m[2] });
      }
    }
    const text = turnMatch[3];
    return {
      kind: "turn",
      turn: parseInt(turnMatch[1], 10),
      role: turnMatch[2],
      text: text.startsWith("(no text") ? null : text,
      tools,
    };
  }

  // Shim event
  const shimMatch = msg.match(SHIM_RE);
  if (shimMatch) {
    return {
      kind: "shim",
      shimType: shimMatch[1] as ShimEvent["shimType"],
      originalPath: shimMatch[2],
      target: shimMatch[3],
    };
  }

  // Death event
  const deathMatch = msg.match(DEATH_RE);
  if (deathMatch) {
    return {
      kind: "death",
      turn: parseInt(deathMatch[1], 10),
    };
  }

  return null;
}
