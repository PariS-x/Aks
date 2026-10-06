"use client";

// Client-side flow for one sitting of Alien Explanation.
// The server owns the game state (timer, violations, understanding, score);
// this hook only sequences screens and keeps a local display clock in sync.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { GameResult, PublicState, VisualProfile } from "@/lib/schemas";

export type Phase = "title" | "creating" | "transmission" | "personalize" | "playing" | "finishing" | "result";

const TERMINAL = new Set(["success", "failed", "timeout"]);

export function useAlienGame(profile: VisualProfile | null) {
  const [phase, setPhase] = useState<Phase>("title");
  const [state, setState] = useState<PublicState | null>(null);
  const [result, setResult] = useState<GameResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [deadline, setDeadline] = useState<number | null>(null);
  const ticking = useRef(false);

  const absorb = useCallback((s: PublicState) => {
    setState(s);
    if (s.status === "playing") setDeadline(Date.now() + s.time_remaining * 1000);
    if (TERMINAL.has(s.status)) {
      setDeadline(null);
      setPhase("finishing");
      api.result(s.game_id).then((r) => {
        setResult(r);
        setPhase("result");
      }).catch((e) => setError(e.message));
    }
  }, []);

  const fail = (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong in transmission.");

  const begin = useCallback(async (personality: string) => {
    setError(null);
    setPhase("creating");
    try {
      const s = await api.createGame({ profile, personality });
      setState(s);
      setResult(null);
      setPhase("transmission");
    } catch (e) {
      fail(e);
      setPhase("title");
    }
  }, [profile]);

  const startRound = useCallback(async () => {
    if (!state) return;
    try {
      const s = await api.start(state.game_id);
      setPhase("playing");
      absorb(s);
    } catch (e) {
      fail(e);
    }
  }, [state, absorb]);

  const afterTransmission = useCallback(() => {
    if (state?.personalization?.themes.length) setPhase("personalize");
    else void startRound();
  }, [state, startRound]);

  const transmit = useCallback(async (text: string) => {
    if (!state || sending) return false;
    setSending(true);
    setError(null);
    try {
      absorb(await api.transmit(state.game_id, text));
      return true;
    } catch (e) {
      fail(e);
      return false;
    } finally {
      setSending(false);
    }
  }, [state, sending, absorb]);

  const tick = useCallback(async () => {
    if (!state || ticking.current) return;
    ticking.current = true;
    try {
      absorb(await api.tick(state.game_id));
    } catch (e) {
      fail(e);
    } finally {
      ticking.current = false;
    }
  }, [state, absorb]);

  const giveUp = useCallback(async () => {
    if (!state) return;
    try {
      absorb(await api.giveUp(state.game_id));
    } catch (e) {
      fail(e);
    }
  }, [state, absorb]);

  const nextSpecimen = useCallback(async () => {
    if (!state) return;
    setError(null);
    setResult(null);
    try {
      const s = await api.next(state.game_id);
      const started = await api.start(s.game_id);
      setPhase("playing");
      absorb(started);
    } catch (e) {
      fail(e);
    }
  }, [state, absorb]);

  const toTitle = useCallback(() => {
    setPhase("title");
    setState(null);
    setResult(null);
  }, []);

  return { phase, state, result, error, sending, deadline, begin, afterTransmission, startRound, transmit, tick, giveUp, nextSpecimen, toTitle, setError };
}

/** Seconds left on the local display clock. Re-renders 4x a second. */
export function useCountdown(deadline: number | null, onZero: () => void) {
  const [now, setNow] = useState(() => Date.now());
  const fired = useRef<number | null>(null);
  useEffect(() => {
    if (!deadline) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [deadline]);
  const left = deadline ? Math.max(0, (deadline - now) / 1000) : 0;
  useEffect(() => {
    if (deadline && left <= 0 && fired.current !== deadline) {
      fired.current = deadline;
      onZero();
    }
  }, [deadline, left, onZero]);
  return left;
}
