import React from "react";
import { Box, Text } from "ink";
import type { FeedEvent, WitnessState } from "../state.js";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface EventFeedProps {
  state: WitnessState;
  height: number;
}

export const EventFeed: React.FC<EventFeedProps> = ({ state, height }) => {
  const events = state.recentEvents.slice(0, height - 2);

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor="gray"
      paddingX={1}
      height={height}
    >
      <Text bold dimColor>
        ▸ Events
      </Text>
      {events.length === 0 ? (
        <Text dimColor>Waiting for log events…</Text>
      ) : (
        events.map((evt: FeedEvent, i: number) => {
          const isDeath = evt.display.includes("[DEATH");
          const isSupp = evt.display.includes("[SUPP]");
          const isShim = evt.display.startsWith("shim(");
          const isText = evt.display.startsWith("~ ");
          const isNoop = evt.display === "(noop)";

          return (
            <Box key={i}>
              <Text color="cyan">
                t{String(evt.turn).padStart(3)}
              </Text>
              <Text> </Text>
              {isDeath ? (
                <Text bold color="red">{evt.display}</Text>
              ) : isSupp ? (
                <Text color="yellow">{evt.display}</Text>
              ) : isShim ? (
                <Text color="magenta">{evt.display}</Text>
              ) : isText ? (
                <Text color="cyan" dimColor>{evt.display}</Text>
              ) : isNoop ? (
                <Text dimColor>{evt.display}</Text>
              ) : (
                <Text>{evt.display}</Text>
              )}
            </Box>
          );
        })
      )}
    </Box>
  );
};
