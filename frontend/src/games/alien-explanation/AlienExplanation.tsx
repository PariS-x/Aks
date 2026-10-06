"use client";

import { Alien } from "@/components/alien/Alien";
import type { VisualProfile } from "@/lib/schemas";
import { GameTitle, Personalize, Transmission } from "./components/Intro";
import { PlayScreen } from "./components/Play";
import { ResultScreen } from "./components/Result";
import { useAlienGame, useCountdown } from "./useAlienGame";

export function AlienExplanation({ profile, onExit }: { profile: VisualProfile | null; onExit: () => void }) {
  const g = useAlienGame(profile);
  const left = useCountdown(g.phase === "playing" ? g.deadline : null, g.tick);

  switch (g.phase) {
    case "title":
    case "creating":
      return <GameTitle onBegin={g.begin} busy={g.phase === "creating"} error={g.error} onExit={onExit} />;
    case "transmission":
      return <Transmission onReady={g.afterTransmission} />;
    case "personalize":
      return (
        <Personalize
          themes={g.state?.personalization?.themes ?? []}
          reason={g.state?.personalization?.reason ?? ""}
          onGo={g.startRound}
        />
      );
    case "playing":
      return g.state ? (
        <PlayScreen state={g.state} left={left} sending={g.sending} error={g.error} onSend={g.transmit} onGiveUp={g.giveUp} />
      ) : null;
    case "finishing":
      return (
        <main className="grid min-h-dvh place-items-center bg-paper text-ink" aria-busy="true">
          <div className="text-center">
            <Alien mood="thinking" className="mx-auto w-48" />
            <p className="display mt-4 text-4xl" role="status">The alien is deciding</p>
          </div>
        </main>
      );
    case "result":
      return g.result && g.state ? (
        <ResultScreen result={g.result} state={g.state} onNext={g.nextSpecimen} onExit={onExit} hasProfile={!!profile} />
      ) : null;
  }
}
