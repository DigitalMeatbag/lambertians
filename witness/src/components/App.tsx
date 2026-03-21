import React from "react";
import { Box, useStdout } from "ink";
import { HudStrip } from "./HudStrip.js";
import { JournalPanel } from "./JournalPanel.js";
import { TextPanel } from "./TextPanel.js";
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

  // HUD occupies 4 rows (2 content + border top/bottom). Body gets the rest.
  const bodyRows = Math.max(rows - 4, 10);

  return (
    <Box flexDirection="column" width="100%">
      <HudStrip state={state} />
      <Box flexDirection="row" width="100%">
        <Box flexGrow={0} flexShrink={0} flexBasis="25%">
          <JournalPanel state={state} height={bodyRows} />
        </Box>
        <Box flexGrow={1} flexShrink={1} flexBasis="45%">
          <TextPanel state={state} height={bodyRows} />
        </Box>
        <Box flexGrow={0} flexShrink={0} flexBasis="30%">
          <EventFeed state={state} height={bodyRows} />
        </Box>
      </Box>
    </Box>
  );
};

