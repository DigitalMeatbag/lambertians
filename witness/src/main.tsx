#!/usr/bin/env node
/**
 * lambertian-witness — live terminal observer for Project Lambertian.
 *
 * Spawns `docker compose logs -f agent`, polls state files from the container,
 * and renders a live Ink UI with HUD, journal, and event feed.
 */

import React, { useReducer, useEffect, useRef, useCallback } from "react";
import { render } from "ink";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

import { LogParser } from "./log-parser.js";
import { pollState, readWorkspaceFile, readMaxAge, readInstanceConfig } from "./docker-reader.js";
import { reducer, initialState, type Action } from "./state.js";
import { App } from "./components/App.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 2_000;
const RENDER_BATCH_MS = 500;

// ---------------------------------------------------------------------------
// Wrapper component that owns the state and side-effects
// ---------------------------------------------------------------------------

const Witness: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const pendingRef = useRef<Action[]>([]);
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Batched dispatch: accumulate actions, flush every RENDER_BATCH_MS
  const batchDispatch = useCallback((action: Action) => {
    pendingRef.current.push(action);
    if (!flushTimerRef.current) {
      flushTimerRef.current = setTimeout(() => {
        const actions = pendingRef.current;
        pendingRef.current = [];
        flushTimerRef.current = null;
        for (const a of actions) {
          dispatch(a);
        }
        dispatch({ type: "TICK" });
      }, RENDER_BATCH_MS);
    }
  }, []);

  // ------ Log stream ------
  useEffect(() => {
    const projectRoot = resolve(__dirname, "..", "..");
    const logProc = spawn("docker", ["compose", "logs", "-f", "--tail", "50", "agent"], {
      cwd: projectRoot,
      stdio: ["ignore", "pipe", "pipe"],
    });

    const parser = new LogParser();
    const rl = createInterface({ input: logProc.stdout! });

    rl.on("line", (line: string) => {
      const event = parser.push(line);
      if (event) {
        batchDispatch({ type: "LOG_EVENT", event });

        // Detect workspace writes from turn events to trigger file reads
        if (event.kind === "turn") {
          for (const tc of event.tools) {
            if (tc.tool === "fs.write" && tc.args.includes("agent-work")) {
              const turnNum = event.turn;
              const filePath = tc.args;
              const filename = filePath.replace(/^runtime\/agent-work\//, "");
              readWorkspaceFile(filePath).then((content) => {
                if (content) {
                  batchDispatch({
                    type: "WORKSPACE_WRITE",
                    turn: turnNum,
                    filename,
                    content,
                  });
                }
              });
            }
          }
        }
      }
    });

    return () => {
      rl.close();
      logProc.kill();
    };
  }, [batchDispatch]);

  // ------ State polling ------
  useEffect(() => {
    const poll = () => {
      pollState().then((result) => {
        batchDispatch({ type: "STATE_POLL", poll: result });
      });
    };

    // Initial poll
    poll();

    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [batchDispatch]);

  // ------ Max age (one-time read) ------
  useEffect(() => {
    readMaxAge().then((maxAge) => {
      dispatch({ type: "SET_MAX_AGE", maxAge });
    });
  }, []);

  // ------ Instance config (one-time read) ------
  useEffect(() => {
    readInstanceConfig().then(({ instanceId, modelName }) => {
      dispatch({ type: "SET_INSTANCE_CONFIG", instanceId, modelName });
    });
  }, []);

  return <App state={state} />;
};

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

const app = render(<Witness />);

// Clean shutdown on SIGINT/SIGTERM
const cleanup = () => {
  app.unmount();
  process.exit(0);
};

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
