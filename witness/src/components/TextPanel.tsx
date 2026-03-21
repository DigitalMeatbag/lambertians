import React from "react";
import { Box, Text } from "ink";
import type { TextEntry, WitnessState } from "../state.js";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface TextPanelProps {
  state: WitnessState;
  height: number;
}

const DIVIDER = "─".repeat(48);

export const TextPanel: React.FC<TextPanelProps> = ({ state, height }) => {
  const entries = state.recentTexts;

  // Rough row budget: title row + border = 2 overhead; each entry = header + body lines + divider
  const innerHeight = Math.max(height - 2, 4);

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor="cyan"
      paddingX={1}
      height={height}
    >
      <Text bold color="cyan">
        ◊ Narration
      </Text>

      {entries.length === 0 ? (
        <Box marginTop={1}>
          <Text dimColor>No text turns recorded yet.</Text>
        </Box>
      ) : (
        <Box flexDirection="column" height={innerHeight} overflow="hidden">
          {entries.map((entry: TextEntry, i: number) => {
            const preview =
              entry.text.length > 220
                ? entry.text.slice(0, 220) + "…"
                : entry.text;

            return (
              <Box key={i} flexDirection="column" marginTop={i > 0 ? 0 : 0}>
                {i > 0 && (
                  <Text dimColor>{DIVIDER}</Text>
                )}
                <Box>
                  <Text bold color="cyan">
                    t{entry.turn}
                  </Text>
                  <Text dimColor color="gray">
                    {" "}
                    [{entry.role}]
                  </Text>
                </Box>
                <Text wrap="wrap">{preview}</Text>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
};
