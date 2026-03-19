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
// OR just: [t42][SELF_PROMPT] text   (tools on next line)
const TURN_START_RE = /\[t(\d+)\]\[([^\]]+)\]\s*(.*)/;

// continuation line:   →tools: fs.list('runtime/')
const TOOLS_LINE_RE = /^\s*→tools:\s+(.+)$/;

// [t42] tool suppression active — suppressed: fs.list, fs.read
const SUPPRESSION_RE =
  /\[t(\d+)\] tool suppression active\s*(?:—|\u2014|--)\s*suppressed:\s*(.+)$/;

// Semantic shim (alias/read): 'WORKSPACE.md' → 'runtime/agent-work/WORKSPACE.md'
const SHIM_RE =
  /Semantic shim \(([^)]+)\):\s*'([^']+)'\s*(?:→|\u2192|->)\s*(?:generator\s*)?'([^']+)'/;

// DEATH_TRIGGER or death-related log lines
const DEATH_RE = /\[t(\d+)\].*(?:DEATH_TRIGGER|death|max_age)/i;

// Tool call format: fs.write('runtime/agent-work/test.txt', 42chars)
// Reset lastIndex each time via matchAll — safe as long as we don't share the regex instance
const TOOL_CALL_RE = /(\w+\.\w+)\('([^']*)'(?:,\s*\d+chars)?\)/g;

// ---------------------------------------------------------------------------
// Parser (stateful — handles multi-line turns)
// ---------------------------------------------------------------------------

interface PendingTurn {
  turn: number;
  role: string;
  text: string | null;
}

/**
 * Stateful log parser. Handles multi-line turn events where the tool list
 * appears on a continuation line (`  →tools: ...`).
 *
 * Call `parser.push(line)` for each raw log line.
 * Returns an event or null.
 */
export class LogParser {
  private pending: PendingTurn | null = null;

  push(raw: string): LogEvent | null {
    // Strip docker compose log prefix: "agent-1  | 2026-03-19 18:27:16,869 INFO ... — "
    const pipeIdx = raw.indexOf(" | ");
    const line = pipeIdx >= 0 ? raw.slice(pipeIdx + 3) : raw;

    // Strip "timestamp LEVEL logger.name — " prefix
    // The separator is an em-dash (—) surrounded by spaces
    const sepIdx = line.search(/ [\u2014-] /);
    const msg = sepIdx >= 0 ? line.slice(sepIdx + 3) : line;

    // If we have a pending turn, check if this is the continuation tools line
    if (this.pending) {
      const toolsMatch = msg.match(TOOLS_LINE_RE);
      if (toolsMatch) {
        const tools = extractToolCalls(toolsMatch[1]);
        const event = buildTurnEvent(this.pending, tools);
        this.pending = null;
        return event;
      }
      // Not a tools continuation — emit the pending turn with no tools and re-process
      const event = buildTurnEvent(this.pending, []);
      this.pending = null;
      // Fall through to process current line
      const downstream = this.processLine(msg);
      return event; // return the flushed pending; downstream is dropped (rare)
    }

    return this.processLine(msg);
  }

  /** Flush any buffered pending turn (call at end-of-stream). */
  flush(): LogEvent | null {
    if (!this.pending) return null;
    const event = buildTurnEvent(this.pending, []);
    this.pending = null;
    return event;
  }

  private processLine(msg: string): LogEvent | null {
    // Suppression (before turn check — suppression lines also have [tN])
    const suppMatch = msg.match(SUPPRESSION_RE);
    if (suppMatch) {
      return {
        kind: "suppression",
        turn: parseInt(suppMatch[1], 10),
        suppressedTools: suppMatch[2].split(",").map((s) => s.trim()),
      };
    }

    // Turn start
    const turnMatch = msg.match(TURN_START_RE);
    if (turnMatch) {
      const rawText = turnMatch[3];
      // Check for inline tools on the same line
      const inlineToolsIdx = rawText.indexOf("  →tools:");
      if (inlineToolsIdx >= 0) {
        const toolsStr = rawText.slice(inlineToolsIdx + 9).trim();
        const text = rawText.slice(0, inlineToolsIdx).trim();
        return buildTurnEvent(
          {
            turn: parseInt(turnMatch[1], 10),
            role: turnMatch[2],
            text: normalizeText(text),
          },
          extractToolCalls(toolsStr)
        );
      }
      // Tools may be on next line — buffer
      this.pending = {
        turn: parseInt(turnMatch[1], 10),
        role: turnMatch[2],
        text: normalizeText(rawText.trim()),
      };
      return null;
    }

    // Shim activation
    const shimMatch = msg.match(SHIM_RE);
    if (shimMatch) {
      return {
        kind: "shim",
        shimType: shimMatch[1] as ShimEvent["shimType"],
        originalPath: shimMatch[2],
        target: shimMatch[3],
      };
    }

    // Death
    const deathMatch = msg.match(DEATH_RE);
    if (deathMatch) {
      return {
        kind: "death",
        turn: parseInt(deathMatch[1], 10),
      };
    }

    return null;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractToolCalls(toolsStr: string): ToolCall[] {
  const tools: ToolCall[] = [];
  const re = /(\w+\.\w+)\('([^']*)'(?:,\s*\d+chars)?\)/g;
  for (const m of toolsStr.matchAll(re)) {
    tools.push({ tool: m[1], args: m[2] });
  }
  return tools;
}

function normalizeText(text: string): string | null {
  if (!text || text.startsWith("(no text")) return null;
  return text;
}

function buildTurnEvent(pending: PendingTurn, tools: ToolCall[]): TurnEvent {
  return {
    kind: "turn",
    turn: pending.turn,
    role: pending.role,
    text: pending.text,
    tools,
  };
}

/**
 * Convenience stateless parse for single-line events that don't need
 * multi-line handling (shims, suppression, death). Used for testing.
 */
export function parseLine(raw: string): LogEvent | null {
  const parser = new LogParser();
  return parser.push(raw);
}
