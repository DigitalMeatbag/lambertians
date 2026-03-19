/**
 * State model for lambertian-witness.
 *
 * Single state object updated by log events, state polls, and workspace
 * writes. The Ink UI renders from this state on a 500ms tick.
 */

import type {
  LogEvent,
  TurnEvent,
  SuppressionEvent,
  ShimEvent,
  ToolCall,
} from "./log-parser.js";
import type { PollResult } from "./docker-reader.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AgentStatus =
  | "ACTIVE"
  | "SUPPRESSED"
  | "NOOP"
  | "DEAD"
  | "WAITING";

export interface LastAction {
  tool: string;
  path: string;
  outcome: "ok" | "fail" | "blocked" | "suppressed";
  turn: number;
}

export interface JournalEntry {
  turn: number;
  filename: string;
  content: string;
  timestamp: number;
}

export interface FeedEvent {
  turn: number;
  display: string;
  timestamp: number;
}

export interface WitnessState {
  instanceId: string;
  turn: number;
  maxAge: number;
  fitness: number | null;
  fitnessEvents: number | null;
  stressScalar: number | null;
  status: AgentStatus;
  suppressedTools: string[];
  lastAction: LastAction | null;
  recentEvents: FeedEvent[];
  journalEntries: JournalEntry[];
  isDead: boolean;
  deathTurn: number | null;
  lastActivityTime: number;

  // Host telemetry
  cpuPercent: number | null;
  memPercent: number | null;
  gpuPercent: number | null;
  mediaPlaying: string | null;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type Action =
  | { type: "LOG_EVENT"; event: LogEvent }
  | { type: "STATE_POLL"; poll: PollResult }
  | { type: "WORKSPACE_WRITE"; turn: number; filename: string; content: string }
  | { type: "SET_MAX_AGE"; maxAge: number }
  | { type: "TICK" };

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

export function initialState(): WitnessState {
  return {
    instanceId: "",
    turn: 0,
    maxAge: 500,
    fitness: null,
    fitnessEvents: null,
    stressScalar: null,
    status: "WAITING",
    suppressedTools: [],
    lastAction: null,
    recentEvents: [],
    journalEntries: [],
    isDead: false,
    deathTurn: null,
    lastActivityTime: 0,
    cpuPercent: null,
    memPercent: null,
    gpuPercent: null,
    mediaPlaying: null,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MAX_FEED_EVENTS = 20;
const MAX_JOURNAL_ENTRIES = 10;
const WAITING_TIMEOUT_MS = 60_000;

function addFeedEvent(
  events: FeedEvent[],
  entry: FeedEvent
): FeedEvent[] {
  return [entry, ...events].slice(0, MAX_FEED_EVENTS);
}

function formatToolCalls(tools: ToolCall[]): string {
  return tools
    .map((t) => {
      const short =
        t.args.length > 40 ? t.args.slice(0, 37) + "..." : t.args;
      return `${t.tool}('${short}')`;
    })
    .join(", ");
}

function deriveStatus(state: WitnessState): AgentStatus {
  if (state.isDead) return "DEAD";
  if (state.suppressedTools.length > 0) return "SUPPRESSED";
  if (Date.now() - state.lastActivityTime > WAITING_TIMEOUT_MS) return "WAITING";
  if (
    state.lastAction &&
    state.lastAction.outcome === "ok" &&
    state.turn > 0
  )
    return "ACTIVE";
  return "ACTIVE";
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export function reducer(state: WitnessState, action: Action): WitnessState {
  switch (action.type) {
    case "LOG_EVENT":
      return handleLogEvent(state, action.event);

    case "STATE_POLL":
      return handleStatePoll(state, action.poll);

    case "WORKSPACE_WRITE":
      return {
        ...state,
        journalEntries: [
          {
            turn: action.turn,
            filename: action.filename,
            content: action.content,
            timestamp: Date.now(),
          },
          ...state.journalEntries,
        ].slice(0, MAX_JOURNAL_ENTRIES),
      };

    case "SET_MAX_AGE":
      return { ...state, maxAge: action.maxAge };

    case "TICK":
      return { ...state, status: deriveStatus(state) };

    default:
      return state;
  }
}

function handleLogEvent(state: WitnessState, event: LogEvent): WitnessState {
  const now = Date.now();

  switch (event.kind) {
    case "turn": {
      const turnEvt = event as TurnEvent;
      const toolDisplay = turnEvt.tools.length > 0
        ? formatToolCalls(turnEvt.tools)
        : turnEvt.text
          ? "(text only)"
          : "(noop)";

      const lastAction: LastAction | null =
        turnEvt.tools.length > 0
          ? {
              tool: turnEvt.tools[0].tool,
              path: turnEvt.tools[0].args,
              outcome: "ok",
              turn: turnEvt.turn,
            }
          : state.lastAction;

      const feedDisplay = toolDisplay;
      const isNoop = turnEvt.tools.length === 0 && !turnEvt.text;

      return {
        ...state,
        turn: turnEvt.turn,
        lastAction,
        lastActivityTime: now,
        suppressedTools: [],
        status: isNoop ? "NOOP" : "ACTIVE",
        recentEvents: addFeedEvent(state.recentEvents, {
          turn: turnEvt.turn,
          display: feedDisplay,
          timestamp: now,
        }),
      };
    }

    case "suppression": {
      const suppEvt = event as SuppressionEvent;
      return {
        ...state,
        turn: suppEvt.turn,
        suppressedTools: suppEvt.suppressedTools,
        lastActivityTime: now,
        status: "SUPPRESSED",
        recentEvents: addFeedEvent(state.recentEvents, {
          turn: suppEvt.turn,
          display: `suppression: ${suppEvt.suppressedTools.join(", ")}  [SUPP]`,
          timestamp: now,
        }),
      };
    }

    case "shim": {
      const shimEvt = event as ShimEvent;
      return {
        ...state,
        lastActivityTime: now,
        recentEvents: addFeedEvent(state.recentEvents, {
          turn: state.turn,
          display: `shim(${shimEvt.shimType}): ${shimEvt.originalPath} → ${shimEvt.target}`,
          timestamp: now,
        }),
      };
    }

    case "death":
      return {
        ...state,
        isDead: true,
        deathTurn: event.turn,
        status: "DEAD",
        lastActivityTime: now,
        recentEvents: addFeedEvent(state.recentEvents, {
          turn: event.turn,
          display: `[DEATH at t${event.turn}]`,
          timestamp: now,
        }),
      };

    default:
      return state;
  }
}

function handleStatePoll(state: WitnessState, poll: PollResult): WitnessState {
  return {
    ...state,
    turn: poll.turn?.turn_number ?? state.turn,
    fitness: poll.fitness?.score ?? state.fitness,
    fitnessEvents: poll.fitness?.meaningful_event_count ?? state.fitnessEvents,
    stressScalar: poll.stress?.scalar ?? state.stressScalar,
    cpuPercent: poll.host?.cpu?.load_percent_total ?? state.cpuPercent,
    memPercent: poll.host?.memory?.used_percent ?? state.memPercent,
    gpuPercent: poll.host?.gpu?.load_percent ?? state.gpuPercent,
    mediaPlaying:
      poll.host?.media?.playing && poll.host.media.title
        ? `${poll.host.media.title}${poll.host.media.artist ? ` — ${poll.host.media.artist}` : ""}`
        : state.mediaPlaying,
  };
}
