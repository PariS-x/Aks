// Client-side registry of AKS creativity games.
// Each game is a self-contained folder (engine lives server-side under
// backend/app/games/<id>/; UI lives here under src/games/<id>/). Only Alien
// Explanation exists today; new games add an entry and a folder.
import type { ComponentType } from "react";
import type { VisualProfile } from "@/lib/schemas";
import { AlienExplanation } from "./alien-explanation/AlienExplanation";

export interface CreativityGameClient {
  id: string;
  name: string;
  tagline: string;
  Component: ComponentType<{ profile: VisualProfile | null; onExit: () => void }>;
}

export const GAMES: CreativityGameClient[] = [
  {
    id: "alien-explanation",
    name: "Alien Explanation",
    tagline: "Explain an Earth object to someone who has never seen Earth.",
    Component: AlienExplanation,
  },
];

export const getGame = (id: string) => GAMES.find((g) => g.id === id) ?? GAMES[0];
