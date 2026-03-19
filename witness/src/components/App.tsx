import React from "react";
import { Box, useStdout } from "ink";
import { HudStrip } from "./HudStrip.js";
import { JournalPanel } from "./JournalPanel.js";
import { EventFeed } from "./EventFeed.js";
import type { WitnessState } from "../state.js";

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------

interface AppProps {
  state: WitnessState;
}

export const App: React.FC<AppProps> = ({ state }) => {
  const { stdout } = useStdout();
  const rows = stdout?.rows ?? 40;

  // Layout: HUD takes 4 rows, remaining split between journal (40%) and feed (60%)
  const bodyRows = Math.max(rows - 4, 10);
  const journalHeight = Math.max(Math.floor(bodyRows * 0.4), 5);
  const feedHeight = Math.max(bodyRows - journalHeight, 5);

  return (
    <Box flexDirection="column">
      <HudStrip state={state} />
      <Box flexDirection="row">
        <Box width="50%">
          <JournalPanel state={state} height={journalHeight} />
        </Box>
        <Box width="50%">
          <EventFeed state={state} height={feedHeight} />
        </Box>
      </Box>
    </Box>
  );
};
