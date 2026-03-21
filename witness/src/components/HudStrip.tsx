import React from "react";
import { Box, Text } from "ink";
import type { WitnessState, AgentStatus } from "../state.js";

// ---------------------------------------------------------------------------
// Status styling
// ---------------------------------------------------------------------------

const STATUS_STYLE: Record<AgentStatus, { label: string; color: string }> = {
  ACTIVE: { label: "● ACTIVE", color: "green" },
  SUPPRESSED: { label: "◐ SUPPRESSED", color: "yellow" },
  NOOP: { label: "○ NOOP", color: "yellow" },
  DEAD: { label: "✕ DEAD", color: "red" },
  WAITING: { label: "… WAITING", color: "gray" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(n: number, max: number): string {
  if (max <= 0) return "—";
  return `${Math.round((n / max) * 100)}%`;
}

function bar(ratio: number, width: number): string {
  const filled = Math.round(ratio * width);
  return "█".repeat(filled) + "░".repeat(width - filled);
}

function formatFloat(n: number | null, decimals = 3): string {
  return n !== null ? n.toFixed(decimals) : "—";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface HudStripProps {
  state: WitnessState;
}

export const HudStrip: React.FC<HudStripProps> = ({ state }) => {
  const s = STATUS_STYLE[state.status];
  const ageRatio =
    state.maxAge > 0 ? Math.min(state.turn / state.maxAge, 1) : 0;
  const ageColor = ageRatio > 0.8 ? "red" : ageRatio > 0.5 ? "yellow" : "green";
  const painHigh = state.stressScalar !== null && state.stressScalar > 0.5;

  const instanceLabel = state.instanceId || "—";
  const modelLabel = state.modelName ?? "…";

  const lastTool = state.lastAction
    ? `${state.lastAction.tool}('${state.lastAction.path.length > 28 ? state.lastAction.path.slice(0, 25) + "..." : state.lastAction.path}')`
    : "—";

  return (
    <Box flexDirection="column" borderStyle="bold" borderColor={s.color} paddingX={1}>
      {/* Row 1: identity + live metrics */}
      <Box>
        <Text dimColor>Λ </Text>
        <Text bold>{instanceLabel}</Text>
        <Text dimColor>  [{modelLabel}]</Text>
        <Text dimColor>  ·  </Text>
        <Text color={s.color} bold>{s.label}</Text>
        <Text dimColor>  │  </Text>
        <Text>
          t<Text bold>{state.turn}</Text>/{state.maxAge}
        </Text>
        <Text dimColor>  │  </Text>
        <Text color={ageColor}>
          {bar(ageRatio, 10)} {pct(state.turn, state.maxAge)}
        </Text>
        <Text dimColor>  │  </Text>
        <Text>
          fit:<Text bold>{formatFloat(state.fitness)}</Text>
        </Text>
        <Text dimColor>  │  </Text>
        <Text>
          pain:<Text bold color={painHigh ? "red" : undefined}>
            {formatFloat(state.stressScalar)}
          </Text>
        </Text>
      </Box>
      {/* Row 2: last action + host telemetry */}
      <Box>
        <Text dimColor>last: </Text>
        <Text>{lastTool}</Text>
        {state.suppressedTools.length > 0 && (
          <>
            <Text dimColor> │ suppressed: </Text>
            <Text color="yellow">{state.suppressedTools.join(", ")}</Text>
          </>
        )}
        {state.cpuPercent !== null && (
          <>
            <Text dimColor> │ cpu:</Text>
            <Text>{state.cpuPercent.toFixed(0)}%</Text>
            <Text dimColor> mem:</Text>
            <Text>{state.memPercent?.toFixed(0) ?? "—"}%</Text>
          </>
        )}
        {state.mediaPlaying && (
          <>
            <Text dimColor> │ ♪ </Text>
            <Text color="cyan">{state.mediaPlaying.slice(0, 30)}</Text>
          </>
        )}
      </Box>
    </Box>
  );
};

