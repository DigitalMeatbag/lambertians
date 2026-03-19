import React from "react";
import { Box, Text } from "ink";
import type { JournalEntry, WitnessState } from "../state.js";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface JournalPanelProps {
  state: WitnessState;
  height: number;
}

export const JournalPanel: React.FC<JournalPanelProps> = ({
  state,
  height,
}) => {
  if (state.isDead) {
    return (
      <Box
        flexDirection="column"
        borderStyle="single"
        borderColor="red"
        paddingX={1}
        height={height}
      >
        <Box justifyContent="center">
          <Text bold color="red">
            ╔══════════════════════════════╗
          </Text>
        </Box>
        <Box justifyContent="center">
          <Text bold color="red">
            ║      DEATH at t{state.deathTurn}      ║
          </Text>
        </Box>
        <Box justifyContent="center">
          <Text bold color="red">
            ╚══════════════════════════════╝
          </Text>
        </Box>
        {state.fitness !== null && (
          <Box justifyContent="center">
            <Text dimColor>
              final fitness: {state.fitness.toFixed(4)} │ events:{" "}
              {state.fitnessEvents ?? "—"} │ pain:{" "}
              {state.stressScalar?.toFixed(3) ?? "—"}
            </Text>
          </Box>
        )}
      </Box>
    );
  }

  const entries = state.journalEntries.slice(0, 5);

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor="blue"
      paddingX={1}
      height={height}
    >
      <Text bold color="blue">
        Journal
      </Text>
      {entries.length === 0 ? (
        <Text dimColor>No workspace writes yet.</Text>
      ) : (
        entries.map((entry: JournalEntry, i: number) => (
          <Box key={i} flexDirection="column" marginTop={i > 0 ? 1 : 0}>
            <Text>
              <Text color="cyan" bold>
                t{entry.turn}
              </Text>
              <Text dimColor> {entry.filename}</Text>
            </Text>
            <Text wrap="truncate-end">
              {entry.content.length > 200
                ? entry.content.slice(0, 200) + "…"
                : entry.content}
            </Text>
          </Box>
        ))
      )}
    </Box>
  );
};
