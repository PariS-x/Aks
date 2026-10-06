"use client";

// AKS: archive -> reflection -> creativity game, as one product.
import { useCallback, useEffect, useState } from "react";
import { Home } from "@/components/aks/Home";
import { Analyzing, Reflection } from "@/components/aks/Reflection";
import { api, ApiError } from "@/lib/api";
import type { VisualProfile } from "@/lib/schemas";
import { getGame } from "@/games/registry";

type View = { name: "home" } | { name: "analyzing"; label: string } | { name: "reflection" } | { name: "game"; id: string };

export function AksApp() {
  const [view, setView] = useState<View>({ name: "home" });
  const [profile, setProfile] = useState<VisualProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: Promise<VisualProfile>, label: string) => {
    setError(null);
    setView({ name: "analyzing", label });
    try {
      const prof = await p;
      setProfile(prof);
      setView({ name: "reflection" });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not read that board.");
      setView({ name: "home" });
    }
  }, []);

  // Deep links: ?demo=<board-id> or ?play=1
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const demo = q.get("demo");
    if (demo) void load(api.demoProfile(demo), `sample archive: ${demo}`);
    else if (q.get("play")) setView({ name: "game", id: "alien-explanation" });
  }, [load]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [view.name]);

  switch (view.name) {
    case "home":
      return (
        <Home
          busy={false}
          error={error}
          onAnalyzeUrl={(url) => load(api.analyzeBoard(url), url)}
          onDemo={(id) => load(api.demoProfile(id), `sample archive: ${id}`)}
          onSkip={() => {
            setProfile(null);
            setView({ name: "game", id: "alien-explanation" });
          }}
        />
      );
    case "analyzing":
      return <Analyzing label={view.label} />;
    case "reflection":
      return profile ? (
        <Reflection profile={profile} onPlay={() => setView({ name: "game", id: "alien-explanation" })} onBack={() => setView({ name: "home" })} />
      ) : null;
    case "game": {
      const { Component } = getGame(view.id);
      return <Component profile={profile} onExit={() => setView(profile ? { name: "reflection" } : { name: "home" })} />;
    }
  }
}
